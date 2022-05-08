#!/usr/bin/python3
import pika
import sys
from subprocess import Popen
from subprocess import PIPE
from datetime import datetime
import json
import re
#magic constants (TODO put it into startup.config)
amqp_namespace = "opensuse.obs";
program_name="./program.py"
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


def callback(ch, method, properties, body):
    #bodyargs=json.loads(body.decode("utf-8"))
    print(datetime.now().strftime("%H:%M:%S"),"[x] %r:%r" % (method.routing_key, body))
    if method.routing_key == amqp_namespace+".package.build_fail":
        print("starting subprocess...") 
        
        bodyargs=json.loads(body)
        #bodyargs=body
        #print(bodyargs)
        filename=bodyargs['project']+"."+bodyargs['repository']+"."+bodyargs['arch']+"."+bodyargs['package'],".json"
        json.dump(body,filename)
        pipe1=Popen(["python3", program_name, "--fileurl", "http://localhost:3000/public/build/"+bodyargs['project']+"/"+bodyargs['repository']+"/"+bodyargs['arch']+"/"+bodyargs['package']+"/_log"],"--pargs",filename, stdout=PIPE)
        #pipe1=Popen(["python3", program_name, "--file", "./_log.txt"], stdout=PIPE)
        print("subprocess answer\n",(pipe1.stdout.read()).decode("utf-8"))
    

channel.basic_consume(
    queue=queue_name, on_message_callback=callback, auto_ack=True)

channel.start_consuming()
