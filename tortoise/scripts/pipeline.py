import os
import boto3
import uuid
import argparse

from typing import Dict, Iterable, List, Tuple

import aws_config

parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=str, help='Audio data dir.', default=None)

def get_audio_files(audio_dir: str) -> Tuple[Dict[str, str], List[str]]:
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
        s3.upload_file(file['file_path'], bucket_name, file['file_name'], ExtraArgs={'ACL':'public-read'})
        location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
        file_url = "https://%s.s3.%s.amazonaws.com/%s" % (bucket_name, location, file['file_name'])
        file_urls.append(file_url)

    return file_urls


def upload_categories(categories: Iterable[str], resource) -> Dict[str, str]:
    table = resource.Table(aws_config.ESSAY_CATEGORY_TABLE_NAME)

    name_to_ids = {}
    for category in categories:
        response = table.query(
            IndexName="byEssayCategoryName",
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(category),
        )
        if "Items" not in response or len(response["Items"]) == 0:
            category_id = str(uuid.uuid4())
            print('Putting new category: ', category)
            table.put_item(
                Item={
                    "id": category_id,
                    "name": category,
                }
            )
        else:
            category_id = response["Items"][0]["id"]
        name_to_ids[category] = category_id
    return name_to_ids


def upload_essays_and_authors(essays_data, resource):

    table = resource.Table(aws_config.AUTHOR_TABLE_NAME)

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

    dynamodb_resource = boto3.resource(
        'dynamodb',
        region_name='us-west-1',
        aws_access_key_id=aws_config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_config.AWS_SECRET_ACCESS_KEY,)

    category_names_to_ids = upload_categories(set(categories), resource=dynamodb_resource)

    essays_data = [
        {
            "id": str(uuid.uuid4()),
            "name": file_urls[x].split('/')[-1].split('.wav')[0],
            "imageUri": aws_config.TEMP_IMAGE_URI,
            "audioUri": file_urls[x],
            "essayCategoryId": category_names_to_ids[categories[x]],
            "authorImageUri": aws_config.TEMP_IMAGE_URI,
            # author name is temporarily needed to get author id
            "author_name": file_urls[x].split('/')[-3]
        } for x in range(len(files))
    ]

    upload_essays_and_authors(essays_data, resource=dynamodb_resource)
