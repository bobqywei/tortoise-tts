import os
import boto3
import uuid
import argparse
from datetime import datetime, timezone

from typing import Dict, Iterable, List, Optional, Set, Tuple

import tortoise.scripts.aws_secret as aws_secret

parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=str, help='Audio data dir.', default=None)
parser.add_argument('--overwrite', action='store_true', help='Overwrite data files.', default=False)


def get_current_time_aws_format() -> str:
    return str(datetime.now(timezone.utc).astimezone().isoformat())


def s3_file_exists(s3_client, bucket: str, file_path: str) -> bool:
    try:
        s3_client.Object(bucket, file_path).load()
    except Exception as _:
        return False
    return True


def get_audio_files(audio_dir: str) -> Tuple[List[Dict[str, str]], Set[str], Set[str], Set[str]]:
    audio_files = []
    authors = set()
    categories = set()
    albums = set()
    for root, _, files in os.walk(audio_dir):
        for file in files:
            if 'combined' not in file:
                continue

            dirs = [d for d in root.split('/') if d]
            category_dir_idx = 0
            while category_dir_idx < len(dirs):
                if '---' in dirs[category_dir_idx]:
                    break
                category_dir_idx += 1

            filename = dirs[-1].split('---')[0]
            category = dirs[category_dir_idx].split('---')[1]
            voice = dirs[category_dir_idx - 1]
            author = dirs[category_dir_idx - 2]
            album = None
            if category_dir_idx + 1 < len(dirs):
                album = dirs[category_dir_idx + 1].split('---')[0]
                albums.add(album)
            audio_files.append({
                'author': author,
                'voice': voice,
                'category': category,
                'name': filename,
                'album': album,
                'file_path': os.path.join(root, file),
            })
            authors.add(author)
            categories.add(category)
    
    return audio_files, authors, categories, albums


def upload_s3(bucket_name, files, overwrite: bool = False):
    s3 = boto3.client(
        's3',
        aws_access_key_id=aws_secret.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_secret.AWS_SECRET_ACCESS_KEY,
    )

    location = s3.get_bucket_location(Bucket=bucket_name)['LocationConstraint']
    file_urls = []
    for file in files:
        if not overwrite and s3_file_exists(s3, bucket_name, file['file_name']):
            s3.upload_file(file['file_path'], bucket_name, file['file_name'], ExtraArgs={'ACL':'public-read'})
        else:
            print('File already exists: ', file['file_name'])
        file_url = 'https://%s.s3.%s.amazonaws.com/%s' % (bucket_name, location, file['file_name'])
        file_urls.append(file_url)

    return file_urls


def upload_named_entity(names: Iterable[str], table, table_query_index: str, image_uris: Optional[Iterable[str]] = None) -> Dict[str, str]:
    if not image_uris:
        image_uris = [None] * len(names)
    name_to_ids = {}
    for name, image_uri in zip(names, image_uris):
        response = table.query(
            IndexName=table_query_index,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(name),
        )
        if 'Items' not in response or len(response['Items']) == 0:
            name_id = str(uuid.uuid4())
            print('Putting new: ', name)
            item = {
                'id': name_id,
                'name': name,
                'createdAt': get_current_time_aws_format(),
                'updatedAt': get_current_time_aws_format(),
            }
            if image_uri:
                item['imageUri'] = image_uri
            table.put_item(Item=item)
        else:
            name_id = response['Items'][0]['id']
        name_to_ids[name] = name_id
    return name_to_ids


def upload_essays(essays_data, dynamodb_resource):
    table = dynamodb_resource.Table(aws_secret.ESSAY_TABLE_NAME)

    for essay in essays_data:
        response = table.query(
            IndexName='byEssayNameAndAuthor',
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(essay['name']) & (
                boto3.dynamodb.conditions.Key('authorId').eq(essay['authorId'])),
        )
        if 'Items' not in response or len(response['Items']) == 0:
            essay['createdAt'] = get_current_time_aws_format()
            essay['updatedAt'] = get_current_time_aws_format()
            print('Putting new essay: ', essay['name'])
            table.put_item(Item=essay)


if __name__ == '__main__':
    args = parser.parse_args()
    audio_dir = args.audio

    files, authors, categories, albums = get_audio_files(audio_dir=audio_dir)
    upload_files_data = [
        {
            'file_name': os.path.join('public/audio', file['author'], file['voice'], file['name'] + '.wav'),
            'file_path': file['file_path'],
            'file_type': 'audio/xwav'
        } for file in files
    ]
    print('Uploading audio to S3...')
    file_urls = upload_s3(aws_secret.S3_BUCKET_NAME, upload_files_data, overwrite=args.overwrite)

    print('Uploading to dynamodb...')
    dynamodb_resource = boto3.resource(
        'dynamodb',
        region_name='us-west-1',
        aws_access_key_id=aws_secret.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=aws_secret.AWS_SECRET_ACCESS_KEY,)

    category_names_to_ids = upload_named_entity(
        categories,
        dynamodb_resource.Table(aws_secret.ESSAY_CATEGORY_TABLE_NAME),
        'byEssayCategoryName')

    author_names_to_ids = upload_named_entity(
        authors,
        dynamodb_resource.Table(aws_secret.AUTHOR_TABLE_NAME),
        'byAuthorName',
        [aws_secret.TEMP_IMAGE_URI] * len(authors))

    album_names_to_ids = upload_named_entity(
        albums,
        dynamodb_resource.Table(aws_secret.ALBUM_TABLE_NAME),
        'byAlbumName',
        [aws_secret.TEMP_IMAGE_URI] * len(albums))
    
    essays_data = []
    for i, file_dict in enumerate(files):
        essays_data.append({
            'id': str(uuid.uuid4()),
            'name': file_dict['name'],
            'imageUri': aws_secret.TEMP_IMAGE_URI,
            'audioUri': file_urls[i],
            'authorId': author_names_to_ids[file_dict['author']],
            'essayCategoryId': category_names_to_ids[file_dict['category']],
            'essayAlbumId': album_names_to_ids[file_dict['album']] if file_dict['album'] else 'NO_ALBUM',
        })

    upload_essays(essays_data, dynamodb_resource)
