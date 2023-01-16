import os
import boto3
import uuid
import argparse

import aws_config

parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=str, help='Audio data dir.', default=None)

def get_audio_files(audio_dir):
    audio_files = []
    categories = []
    for root, dirs, files in os.walk(audio_dir):
        for file in files:

            if 'combined' not in file:
                continue
            filename, category = root.split('---')[0].split('/')[-1], root.split('---')[1]
            author = root.split('/')[-3]
            voice = root.split('/')[-2]
            audio_files.append({
                'file_name': 'public/audio/' + author + '/' + voice + '/' + filename + '.wav',
                'file_path': os.path.join(root, file),
                'file_type': 'audio/xwav'
            })
            categories.append(category.split('.wav')[0])
    
    return audio_files, categories


def upload_s3(bucket_name, files):

    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_config.AWS_SECRET_ACCESS_KEY,
    )

    file_urls = []
    for file in files:
        s3.upload_file(file['file_path'], bucket_name, file['file_name'])
        file_url = '%s/%s/%s' % (s3.meta.endpoint_url, bucket_name, file['file_name'])
        file_urls.append(file_url)

    return file_urls


def upload_dynamo_db(essays_data, category_data):

    dynamodb_resource = boto3.resource(
        'dynamodb',
        region_name='us-west-1',
        aws_access_key_id=aws_config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_config.AWS_SECRET_ACCESS_KEY,)

    table = dynamodb_resource.Table(aws_config.AUTHOR_TABLE_NAME)

    for essay in essays_data:
        author_name = essay["author_name"]
        response = table.query(
            IndexName="byAuthorName",
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(author_name),
        )
        if "Items" not in response or len(response["Items"]) == 0:
            author_id = str(uuid.uuid4())
            print('Putting new author: ', author_name)
            table.put_item(
                Item={
                    "id": author_id,
                    "name": essay["author_name"],
                    "imageUri": essay["authorImageUri"]
                }
            )
            essay['authorId'] = author_id
        else:
            essay['authorId'] = response["Items"][0]["id"]

        essay.pop('author_name')

    essay_table = dynamodb_resource.Table(aws_config.ESSAY_TABLE_NAME)
    for essay in essays_data:
        response = essay_table.query(
            IndexName="byEssayNameAndAuthor",
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(essay['name']) & (
                boto3.dynamodb.conditions.Key('authorId').eq(essay['authorId'])),
        )
        if "Items" not in response or len(response["Items"]) == 0:
            print('Putting new essay: ', essay['name'])
            essay_table.put_item(Item=essay)
    
    category_table = dynamodb_resource.Table(aws_config.ESSAY_CATEGORY_TABLE_NAME)
    for category in category_data:
        response = category_table.query(
            IndexName="byEssayCategoryName",
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(category['name']))
        if "Items" not in response or len(response["Items"]) == 0:
            print('Putting new category: ', category['name'])
            category_table.put_item(Item=category)


if __name__ == '__main__':
    args = parser.parse_args()
    audio_dir = args.audio

    files, categories = get_audio_files(audio_dir=audio_dir)
    file_urls = upload_s3(aws_config.S3_BUCKET_NAME, files)

    # with open('file_urls.txt', 'w') as f:
    #     for url in file_urls:
    #         f.write(url + '\n')

    # with open('file_urls.txt', 'r') as f:
    #     file_urls = f.readlines()

    essays_data = [
        {
            "id": str(uuid.uuid4()),
            "name": file_urls[x].split('/')[-1].split('.wav')[0],
            "imageUri": "s3://spotifye549ed42da7f4fada97d00a50269aa43154513-default/public/author_images/paul_graham.png",
            "audioUri": file_urls[x],
            "essayCategoryId": categories[x],
            "authorImageUri": "s3://spotifye549ed42da7f4fada97d00a50269aa43154513-default/public/author_images/paul_graham.png",
            # author name is temporarily needed to get author id
            "author_name": file_urls[x].split('/')[-3]
        } for x in range(len(files))
    ]
    categories_data = [
        {
            "id": str(uuid.uuid4()),
            "name": category
        } for category in set(categories)
    ]
    upload_dynamo_db(essays_data, categories_data)
