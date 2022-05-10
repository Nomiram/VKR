#!/usr/bin/python3
import pika
import sys
from subprocess import Popen
from subprocess import PIPE
from datetime import datetime
import json
import re
from jira import JIRA
#magic constants (TODO put it into startup.config)
amqp_namespace = "opensuse.obs";
program_name = "./logAnalizer"
JIRAOPTIONSFILENAME = "jira_api_key.json"
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='pubsub', exchange_type='topic')
result=channel.queue_declare('', exclusive=True)
queue_name=result.method.queue

binding_keys = "#"
if not binding_keys:
    sys.stderr.write("Usage: %s [binding_key]...\n" % sys.argv[0])
    sys.exit(1)
    
for i in range(len(binding_keys)):
    channel.queue_bind(
        exchange='pubsub', queue=queue_name, routing_key=binding_keys)
    

print(datetime.now().strftime("%H:%M:%S"),' [*] Waiting for logs. To exit press CTRL+C')

def JiraNotifySender(project_key,summary,message):
    with open(str(JIRAOPTIONSFILENAME), 'r') as fp:
        server, login, api_key=json.load(fp)
        fp.close()
    if not api_key:
        print("unable to read file 'jira_api_key.json'")
        exit()
    jira_options = {'server': server}
    jira = JIRA(options=jira_options, basic_auth=(login, api_key))
    issue_key="JPAT-1"
    issue = jira.issue(issue_key)
    #print(issue)
    try:
        project_key 
    except Exception:
        print("error: project_key not found ")
        return
    jql = 'project = ' + project_key
    issues_list = jira.search_issues(jql)
    #print(issues_list)
    issue_dict = {
        'project': project_key,
        'summary': summary,
        'description': message,
        'issuetype': {'name': 'Task'}
    }
    new_issue = jira.create_issue(fields=issue_dict)
def callback(ch, method, properties, body):
    #bodyargs=json.loads(body.decode("utf-8"))
    print(datetime.now().strftime("%H:%M:%S"),"[x] %r:%r" % (method.routing_key, body))
    #Detecting down workers
    if method.routing_key == amqp_namespace+".metrics":
        #print("starting subprocess...") 
        
        if ("worker" in str(body)) and ("state=down" in str(body)):
            print("Worker is down. Send notification...")
            JiraNotifySender("DEVOPS",'Local OBS instance error',"Local OBS instance error: Worker is down\n metrics: "+str(body))
    # Detecting and analizing failed packages
    if method.routing_key == amqp_namespace+".package.build_fail":
        print("starting subprocess...") 
        
        bodyargs=json.loads(body)
        #bodyargs=body
        #print(bodyargs)
        filename=bodyargs['project']+"."+bodyargs['repository']+"."+bodyargs['arch']+"."+bodyargs['package']+datetime.now().strftime("-%H-%M-%S")+".json"
        with open(str(filename), 'w') as fp:
            json.dump(bodyargs,fp)
            fp.close()
        pipe1=Popen(["python3", program_name, "--fileurl", "http://localhost:3000/public/build/"+bodyargs['project']+"/"+bodyargs['repository']+"/"+bodyargs['arch']+"/"+bodyargs['package']+"/_log","--pargs",filename], stdout=PIPE)
        #pipe1=Popen(["python3", program_name, "--file", "./_log.txt"], stdout=PIPE)
        print("subprocess answer\n",(pipe1.stdout.read()).decode("utf-8"))
    

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()
