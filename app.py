import boto3
import time
import os

from random import choice
from string import ascii_letters, digits
from flask import Flask, render_template, flash, request
from wtforms import Form, TextField, TextAreaField, validators, StringField, SubmitField


# static global flags
class Flags:
  msg_found = False
  bind = False
  fifo_queue = False

# App config.
#DEBUG = True
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = '43e441fcffed44e3d1bafe37'
 
class SendMsgForm(Form):
    msg = TextField('Message:', validators=[validators.required()])

@app.route("/", methods=['GET'])
def index():
  if not flags.bind :
    flash("ERROR: The app has not been binded yet!")
  else :
    flash("Select from below to continue:")
  return render_template('index.html')

@app.route("/send", methods=['GET', 'POST'])
def send():
  form = SendMsgForm(request.form)
  print (form.errors)
  if (request.method == 'GET') :
    flash("Type your message and click the 'Send' button.")
  else: # request.method == 'POST'
    msg=request.form['msg']
    print ("sending msg : \'", msg, "\'")
    msgDedupId="".join(choice(ascii_letters + digits) for i in range(128))
    msgGroupId="".join(choice(ascii_letters + digits) for i in range(128))
    if form.validate():
      try:
        if flags.fifo_queue :
          response = client.send_message(QueueUrl=sqs_queue_url, MessageBody=msg,
                                         MessageDeduplicationId=msgDedupId,
                                         MessageGroupId=msgGroupId)
        else:
          response = client.send_message(QueueUrl=sqs_queue_url, MessageBody=msg)
        if response['ResponseMetadata']['HTTPStatusCode'] != 200:
          flash('ERROR: Msg Send FAILED! HTTPStatusCode:' +
                response['ResponseMetadata']['HTTPStatusCode'])
        else:
          flash('Message \"'+ msg + '\" was sent! ')
      except:
        flash('ERROR: Invalid response from client!')
    else:
        flash('ERROR: Enter a valid message!')
  return render_template('send.html', form=form)

@app.route("/read", methods=['GET', 'POST'])
def read():
  if (request.method == 'GET') :
    flash("Click the 'Read' button.")
  else: # request.method == 'POST'
    # Receive messages and delete them
    flags.msg_found = False
    for i in range(max_retry) :
      try:
        result = client.receive_message(QueueUrl=sqs_queue_url,
                                        MaxNumberOfMessages=max_num_msgs,
                                        VisibilityTimeout=vis_timeout,
                                        WaitTimeSeconds=wait_sec)
        flash("Message: " + result["Messages"][0]["Body"])
        flash("Click again to read another message.")
        client.delete_message(QueueUrl=sqs_queue_url,
                              ReceiptHandle=result["Messages"][0]["ReceiptHandle"])
        flags.msg_found = True
        break
      except:
        pass
    if not flags.msg_found:
      flash("No Messages Found!")
  return render_template('read.html', form=request.form)

if __name__ == "__main__":

  flags = Flags()

  max_retry=1
  max_num_msgs=10
  vis_timeout=10
  wait_sec=10

  aws_service="sqs"
  aws_key_id=os.environ.get('SQS_AWS_ACCESS_KEY')
  aws_secret=os.environ.get('SQS_AWS_SECRET_KEY')
  aws_region=os.environ.get('SQS_REGION')
  sqs_queue_url=os.environ.get('SQS_QUEUE_URL')

  if (aws_key_id and aws_secret and aws_region and sqs_queue_url) :
    flags.bind = True
    if "fifo" in sqs_queue_url :
      print ("This is a FIFO Queue")
      flags.fifo_queue = True
    else:
      print ("This is a Standard Queue")
    try:
      client = boto3.client(aws_service,
                            region_name=aws_region,
                            aws_access_key_id=aws_key_id,
                            aws_secret_access_key=aws_secret)
    except:
      print ("ERROR: The AWS client is Invalid!")
      pass
  else :
    print ("The AWS secrets are NOT available! (probably not binded yet)")

  app.run(host='0.0.0.0', port=8080, debug=True)
