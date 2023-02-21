import os
import boto3
import uuid
import argparse
from datetime import datetime, timezone

from typing import Dict, Iterable, List, Optional, Set, Tuple

import tortoise.scripts.aws_secret as aws_secret

_NO_ALBUM_DEFAULT = 'NO_ALBUM'

parser = argparse.ArgumentParser()
parser.add_argument('--audio', type=str, help='Audio data dir.', default=None)
parser.add_argument('--img', type=str, help='Image data dir.', default=None)
parser.add_argument('--overwrite', action='store_true', help='Overwrite data files.', default=False)
parser.add_argument('--voices', type=str, help='Comma separated list of voices to upload.', default='lj,train_dotrice')


def get_current_time_aws_format() -> str:
    return str(datetime.now(timezone.utc).astimezone().isoformat())


def s3_file_exists(s3_client, bucket: str, file_path: str) -> bool:
    try:
        s3_client.head_object(Bucket=bucket, Key=file_path)
    except Exception as _:
        return False
    return True


def get_image_files(dir: str):

    def get_images_from_dir(extension: str):
        path = os.path.join(dir, extension)
        images = []
        if os.path.exists(path):
            for root, _, files in os.walk(path):
                for f in files:
                    if f.endswith('.png'):
                        title = root.split('/')[-1]
                        images.append({
                            'file_name': os.path.join(*filter(lambda x: x, ['public', 'images', extension, title])),
                            'file_path': os.path.join(root, f),
                            'file_type': 'image/png'
                        })
        return images
 
    author_images = get_images_from_dir('authors')
    album_images = get_images_from_dir('albums')
    essay_images = get_images_from_dir('essays')

    return author_images, album_images, essay_images


def get_audio_files(
    audio_dir: str,
    voices: Iterable[str]):
    audio_files = []
    authors = set()
    categories = set()
    albums = {}
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

            voice = dirs[category_dir_idx - 1]
            if voice not in voices:
                continue

            filename = dirs[-1].split('---')[0]
            category = dirs[category_dir_idx].split('---')[-1]
            author = dirs[category_dir_idx - 2]

            album = None
            album_index = None
            # Albums contain the category name one level up in the directory structure.
            # Standalone essays contain the category name in the essay name itself.
            if category_dir_idx < len(dirs) - 1:
                album = dirs[category_dir_idx].split('---')[0]
                album_index = int(dirs[-1].split('---')[-1])
                if not album in albums:
                    albums[album] = (category, author)

            audio_files.append({
                'author': author,
                'voice': voice,
                'category': category,
                'name': filename,
                'album': album,
                'file_path': os.path.join(root, file),
                'album_index': album_index,
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
            print('File already exists: ', file['file_name'])
        else:
            print('Uploading: ', file['file_name'])
            s3.upload_file(file['file_path'], bucket_name, file['file_name'], ExtraArgs={'ACL':'public-read'})
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


def upload_authored_items(data, table, index_name):
    name_author_to_ids = {}

    for d in data:
        response = table.query(
            IndexName=index_name,
            KeyConditionExpression=boto3.dynamodb.conditions.Key('name').eq(d['name']) & (
                boto3.dynamodb.conditions.Key('authorId').eq(d['authorId'])),
        )
        if 'Items' not in response or len(response['Items']) == 0:
            d['id'] = str(uuid.uuid4())
            d['createdAt'] = get_current_time_aws_format()
            d['updatedAt'] = get_current_time_aws_format()
            print('Putting new authored item: ', d['name'])
            table.put_item(Item=d)
        else:
            d['id'] = response['Items'][0]['id']
        name_author_to_ids[(d['name'], d['authorId'])] = d['id']
    
    return name_author_to_ids


if __name__ == '__main__':
    args = parser.parse_args()
    audio_dir = args.audio
    img_dir = args.img

    files, authors, categories, albums_to_category_author = get_audio_files(audio_dir=audio_dir, voices=args.voices.split(','))
    upload_files_data = [{
        'file_name': os.path.join(*map(str, filter(
            lambda x: x is not None,
            ['public/audio', file['author'], file['voice'], file['album'], file['album_index'], file['name'] + '.wav']))),
        'file_path': file['file_path'],
        'file_type': 'audio/xwav'} for file in files]

    author_imgs_data, album_imgs_data, essay_imgs_data = get_image_files(dir=img_dir)

    print('Uploading audio to S3...')
    file_urls = upload_s3(aws_secret.S3_BUCKET_NAME, upload_files_data, overwrite=args.overwrite)

    print('Uploading images to S3...')
    author_image_urls = upload_s3(aws_secret.S3_BUCKET_NAME, author_imgs_data, overwrite=args.overwrite)
    album_image_urls = upload_s3(aws_secret.S3_BUCKET_NAME, album_imgs_data, overwrite=args.overwrite)
    essay_image_urls = upload_s3(aws_secret.S3_BUCKET_NAME, essay_imgs_data, overwrite=args.overwrite)

    author_to_img_url = {d['file_name'].split('/')[-1].split('.')[0]: u for d, u in zip(author_imgs_data, author_image_urls)}
    album_to_img_url = {d['file_name'].split('/')[-1].split('.')[0]: u for d, u in zip(album_imgs_data, album_image_urls)}
    essay_to_img_url = {d['file_name'].split('/')[-1].split('.')[0]: u for d, u in zip(essay_imgs_data, essay_image_urls)}

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
        [author_to_img_url[a] if a in author_to_img_url else aws_secret.DEFAULT_AUTHOR_IMAGE_URI for a in authors])

    albums_data = []
    for i, (album, (category, author)) in enumerate(albums_to_category_author.items()):
        albums_data.append({
            'name': album,
            'imageUri': album_to_img_url[f'{author}---{album}'],
            'authorId': author_names_to_ids[author],
            'categoryId': category_names_to_ids[category],
        })
    album_author_to_ids = upload_authored_items(albums_data, dynamodb_resource.Table(aws_secret.ALBUM_TABLE_NAME), 'byAlbumNameAndAuthor')
    
    essays_data = []
    for i, f in enumerate(files):
        # Temporary hack to only upload lj
        if f['voice'] != 'lj':
            continue
        author_id = author_names_to_ids[f['author']]
        essays_data.append({
            'id': str(uuid.uuid4()),
            'name': f['name'],
            'imageUri': essay_to_img_url['---'.join(map(str, filter(lambda x: x, [
                f['author'],
                f['album'] if f['album'] else _NO_ALBUM_DEFAULT,
                f['name'],
            ])))],
            'audioUri': file_urls[i],
            'authorId': author_id,
            'essayCategoryId': category_names_to_ids[f['category']],
            'essayAlbumId': album_author_to_ids[(f['album'], author_id)] if f['album'] else _NO_ALBUM_DEFAULT,
            'albumIndex': f['album_index'] if f['album_index'] else -1,
        })

    upload_authored_items(essays_data, dynamodb_resource.Table(aws_secret.ESSAY_TABLE_NAME), 'byEssayNameAndAuthor')
