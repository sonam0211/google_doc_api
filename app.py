import os
import google.oauth2.credentials
from flask import Flask, render_template, redirect, request, session, url_for
from requests_oauthlib import OAuth2Session
from googleapiclient.discovery import build
from apiclient.http import MediaFileUpload
from settings import client_id, client_secret, redirect_uri,\
    authorization_base_url, token_url, scope

app = Flask(__name__)
app.secret_key = 'top secret!'

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

@app.route('/')
def index():
    if 'oauth_token' not in session:
        return render_template('index.html')
    else:
        return redirect(url_for('home'))

@app.route('/authorize')
def authorize():
    google_auth = OAuth2Session(
        client_id,
        scope=scope,
        redirect_uri=redirect_uri)
    authorization_url, state = google_auth.authorization_url(
        authorization_base_url,
        access_type='offline',
        prompt='consent',
        include_granted_scopes='true')
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/callback')
def callback():
    google_auth = OAuth2Session(
        client_id,
        scope=scope,
        redirect_uri=redirect_uri,
        state=session['oauth_state'])
    token = google_auth.fetch_token(
        token_url,
        client_secret=client_secret,
        authorization_response=request.url)
    session['oauth_token'] = token
    return redirect(url_for('home'))

@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'oauth_token' not in session:
        return redirect(url_for('index'))

    access_token = session['oauth_token']['access_token']
    refresh_token = session['oauth_token']['refresh_token']
    credentials = google.oauth2.credentials.Credentials(
        access_token,
        refresh_token=refresh_token,
        token_uri=token_url,
        client_id=client_id,
        client_secret=client_secret)
    drive = build('drive', 'v3', credentials=credentials)
    if request.method == 'GET':
        results = drive.files().list(
            q="appProperties has { key='myapp' and value='secret' }",
            pageSize=10,
            fields="nextPageToken, files(id, name)"
        ).execute()
        items = results.get('files', [])
        return render_template('home.html', items=items)
    if request.method == 'POST':
        with open("output.txt", "w") as text_file:
            print(request.form.getlist('textdata')[0], file=text_file)
        file_metadata = {
            'name': request.form.getlist('name')[0],
            'mimeType': 'application/vnd.google-apps.document',
            'appProperties': {
                'myapp': 'secret'
            }
        }
        media = MediaFileUpload('output.txt',
                        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                        resumable=True)
        file = drive.files().create(body=file_metadata,
                                    media_body=media,
                                    fields='id').execute()
        return redirect(url_for('home'))

@app.route('/clear')
def clear():
  if 'oauth_token' in session:
    del session['oauth_token']
  return redirect(url_for('index'))

app.run(debug=True, port=5000)
