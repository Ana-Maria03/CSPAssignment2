import datetime
import os
from flask import Flask, render_template, request, Response, redirect, url_for, flash, send_from_directory, make_response
from google.cloud import datastore, storage
from werkzeug.utils import secure_filename
import google.oauth2.id_token
from google.auth.transport import requests
import local_constants

credential_path = "C:/Users/Ana Maria Macedo/OneDrive/Documents/Cloud Computing/Assignment2/assignment2csp-84a58d4f58f1.json"
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
app = Flask(__name__)


datastore_client = datastore.Client()
firebase_request_adapter = requests.Request()


ALLOWED_EXTENSIONS = {'docx', 'odt', 'xlsx', 'ods'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def createUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore.Entity(key=entity_key)
    entity.update({
        'email': claims['email'],
        'name': claims.get('name', 'Unknown'),
    })
    datastore_client.put(entity)


def retrieveUserInfo(claims):
    entity_key = datastore_client.key('UserInfo', claims['email'])
    entity = datastore_client.get(entity_key)
    return entity


def blobList(prefix):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    return storage_client.list_blobs(local_constants.PROJECT_STORAGE_BUCKET, prefix=prefix)


def addDirectory(directory_name):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(directory_name)
    blob.upload_from_string(
        '', content_type='application/x-www-formurlencoded;charset=UTF-8')


def addFile(file, directory_name):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    filename = secure_filename(file.filename)
    if not allowed_file(filename):
        return "Invalid file format", 400
    blob_name = os.path.join(directory_name, filename)
    blob = bucket.blob(blob_name)
    blob.upload_from_file(file)


def downloadFile(filename):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(filename)
    return blob.download_as_bytes()


def deleteFile(filename):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(filename)
    if blob.exists():
        blob.delete()
    else:
        raise ValueError("File does not exist.")


def shareFile(filename, email):
    storage_client = storage.Client(project=local_constants.PROJECT_NAME)
    bucket = storage_client.bucket(local_constants.PROJECT_STORAGE_BUCKET)
    blob = bucket.blob(filename)

    acl = blob.acl
    acl.all().grant_read()
    acl.save()

    metadata = blob.metadata or {}
    if 'shared_with' in metadata:
        metadata['shared_with'].append(email)
    else:
        metadata['shared_with'] = [email]
    blob.metadata = metadata
    blob.patch()


@ app.route('/add_directory', methods=['POST'])
def addDirectoryHandler():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            directory_name = request.form['dir_name']
            if directory_name == '' or directory_name[len(directory_name) - 1] != '/':
                return redirect('/')

            user_info = retrieveUserInfo(claims)
            addDirectory(directory_name)

        except ValueError as exc:
            error_message = str(exc)
        return redirect('/')


@app.route('/download_file/<filename>', methods=['POST'])
def downloadFileHandler(filename):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_info = retrieveUserInfo(claims)

        except ValueError as exc:
            error_message = str(exc)
    return Response(downloadFile(filename), mimetype='application/octet-stream')


@app.route('/share_file/<filename>', methods=['POST'])
def shareFileHandler(filename):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            email = request.form.get("email")
            shareFile(filename, email)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@ app.route('/upload_file', methods=['POST'])
def uploadFileHandler():
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            file = request.files['file_name']
            directory_name = request.form['dir_name']
            print(directory_name)
            if file.filename == '':
                return redirect('/')
            if not allowed_file(file.filename):
                return "Invalid file format", 400

            user_info = retrieveUserInfo(claims)
            addFile(file, directory_name)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@app.route('/delete_file/<filename>', methods=['POST'])
def deleteFileHandler(filename):
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None
    user_info = None
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            deleteFile(filename)
        except ValueError as exc:
            error_message = str(exc)
    return redirect('/')


@ app.route('/')
def root():

    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    times = None
    user_info = None
    file_list = []
    directory_list = []
    if id_token:
        try:
            claims = google.oauth2.id_token.verify_firebase_token(id_token,
                                                                  firebase_request_adapter)
            user_info = retrieveUserInfo(claims)
            if user_info == None:
                createUserInfo(claims)
                user_info = retrieveUserInfo(claims)
            blob_list = blobList(None)
            for i in blob_list:
                print(i)
                if i.name[len(i.name) - 1] == '/':
                    directory_list.append(i)
                else:
                    file_list.append(i)
        except ValueError as exc:
            error_message = str(exc)

    return render_template('index.html', user_data=claims, times=times, error_message=error_message, user_info=user_info, file_list=file_list, directory_list=directory_list)


if __name__ == '__main__':
    app.run(host="127.0.0.1", port=8080, debug=True)
