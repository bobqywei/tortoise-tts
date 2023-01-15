import boto3
import os


def get_audio_files():
    
    rootdir = os.path.dirname(os.path.realpath(__file__))

    counter = 0
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            print(os.path.join(subdir, file))
            counter += 1
    print(counter)

get_audio_files()

# def upload_s3(bucket_name):

#     # Set up a client to the S3 service
#     s3 = boto3.client('s3')

#     # Set the name of the S3 bucket
#     bucket_name = 'raw-audio'

#     # List of files to upload
#     files = [
#         {
#             'file_name': 'gatsby.jpg',
#             'file_path': '/path/to/gatsby.jpg',
#             'file_type': 'image/jpeg'
#         },
#         {
#             'file_name': 'mockingbird.jpg',
#             'file_path': '/path/to/mockingbird.jpg',
#             'file_type': 'image/jpeg'
#         },
#         {
#             'file_name': 'gatsby.mp3',
#             'file_path': '/path/to/gatsby.mp3',
#             'file_type': 'audio/mpeg'
#         },
#         {
#             'file_name': 'mockingbird.mp3',
#             'file_path': '/path/to/mockingbird.mp3',
#             'file_type': 'audio/mpeg'
#         },
#     ]

#     # Iterate through the files and upload them to S3
#     for file in files:
#         s3.upload_file(file['file_path'], bucket_name, file['file_name'], ExtraArgs={'ContentType': file['file_type']})


# def upload_dynamodb():

#     # Set up a client to the DynamoDB service
#     dynamodb = boto3.client('dynamodb')

#     # Create a list of essay items to be added to the table
#     essay_list = [
#         {
#             'id': {'S': 'essay1'},
#             'name': {'S': 'The Great Gatsby'},
#             'imageUri': {'S': 'https://example.com/gatsby.jpg'},
#             'audioUri': {'S': 'https://example.com/gatsby.mp3'},
#             'essayCategoryId': {'S': 'category1'},
#             'authorId': {'S': 'author1'}
#         },
#         {
#             'id': {'S': 'essay2'},
#             'name': {'S': 'To Kill a Mockingbird'},
#             'imageUri': {'S': 'https://example.com/mockingbird.jpg'},
#             'audioUri': {'S': 'https://example.com/mockingbird.mp3'},
#             'essayCategoryId': {'S': 'category2'},
#             'authorId': {'S': 'author2'}
#         }
#     ]

#     # Use the DynamoDB BatchWriteItem API to add the essays to the table
#     respons            'Item': essay
#                     }
#             e = dynamodb.batch_write_item(
#         RequestItems={
#             'EssayTable': [
#                 {
#                     'PutRequest': {
#             } for essay in essay_list
#             ]
#         }
#     )

#     # Print the response to check for any errors
#     print(response)
