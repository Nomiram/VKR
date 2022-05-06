#!/usr/bin/python3
# Language     : python 3.7 
# Project Name : Parsing & analysing log files
# Author       : nomiram 
# Created      : 22.11.2021 
# Last Modified: 28.11.2021 
# Description  : This program parse logfile from obs and send notifications to developers
# Requirements : regex.config, classifier.config in directory of program
# Requirements : 
import io
import os
import re
import time
import argparse
import json
import requests 
import shutil
'''
TODO
добавить комментарии
добавить класс Classes
добавить класс Conditions
добавить класс Notifications
'''
def printd2(*args, **kwargs):
    if DEBUG==2:
        print(*args, **kwargs)
def printd(*args, **kwargs):
    if DEBUG>=1:
        print(*args, **kwargs)
# Главная функция
def main():
    global DEBUG
    DEBUG=1
    parser = argparse.ArgumentParser(description='Прототип системы анализа и классификации журналов при сборках')
    parser.add_argument("--file",default="", help="Путь к файлу журнала для разбора")
    parser.add_argument("--fileurl",default="", help="Url  путь к файлу журнала для разбора")
    parser.add_argument("--debug",default=0, nargs='?', const=1, help="Включает режим DEBUG")
    args = parser.parse_args()
    if not DEBUG: DEBUG=int(args.debug)
    c1=InputManager()
    
    print("Загрузка конфигурации....",end="")
    confRE,confCl,cond=c1.getConfigs()
    if (confRE==0 or confCl==0 or cond==0):
        print("Неуспешно")
        exit()
    print("Успешно")
    printd2("conditions:",cond)
    printd2("regex:",confRE)
    printd2("cl:",confCl)
    test=c1.JSONload("classifier.json")
    # printd2("conditions json:",test["conditions"])
    if(isinstance(args.file, str)):
        srch1=SearchEngine(confRE,confCl,args.file,args.fileurl)
    else:
        print("ERROR: --file должен содержать строку")
        exit()
    printd2("Поиск:")
    result=srch1.startFind()
    # print(*result)
    notif1=NotifySender(confRE,confCl,cond,result)
    print("Проверка условий")
    print("Отправка ообщений")
    notif1.checkConditions(cond)
    # print(notif1.lasterr())

# Заглушка для класса
class ErrorСauseChecker:
    """Класс предназначен для поиска причины ошибки"""
    def __init__(self,confRE,confCl,strlist,file=""):
        self.confRE,self.confCl=confRE,confCl
        self.inp1=InputManager()
        self.logfile=self.inp1.getLogfile(file,fileurl)

        
class NotifySender:
    """Класс предназначен для уведомления о провалившейся сборке"""
    def __init__(self,confRE,confCl,cond,strlist,file=""):
        self.confRE,self.confCl=confRE,confCl
        self.inp1=InputManager()
        self.logfile=self.inp1.getLogfile(file) 
        self.strlist=strlist
        self.cond=cond
        
    def lasterr(self):
        try:
            return self.strlist[-1]
        except Exception:
            return {"string":"<No errors>","class":-1,"match":"<No errors>"}
        
    def firsterr(self):
        try:
            return self.strlist[0]
        except Exception:
            return {"string":"<No errors>","class":-1,"match":"<No errors>"}
        
    def cntErrClass(self,num):
        return [int(self.strlist[i]["class"]) for i in range(len(self.strlist))].count(int(num))
        
    def replaceKeywords(self,mainstr,str1={"string":"","class":""},type=1):
        mainstr=mainstr.replace("$lasterr",str(self.lasterr()["string"]))
        mainstr=mainstr.replace("$firsterr",str(self.firsterr()["string"]))
        mainstr=mainstr.replace("$txterr",str(str1["string"]))
        mainstr=mainstr.replace("$curerr",str(str1["class"]))
        res=re.findall(r"\$errtxt\[(-*\d)]",mainstr)
        for i in res:
            mainstr=re.sub(r"\$errtxt\[-*{0}]".format(int(i)), str(self.strlist[int(i)]["string"]), mainstr)  
        res=re.findall(r"\$errtxt\[all]",mainstr)
        mainstr=re.sub(r"\$errtxt\[all]", "".join(["".join([str(i["string"]),"\n"]) for i in self.strlist]), mainstr)  
        mainstr=mainstr.replace("$errcnt",str(len(self.strlist)))
        res=re.findall(r"\$numerr\[(-*\d)]",mainstr)
        for i in res:
            mainstr=re.sub(r"\$numerr\[-*{0}]".format(int(i)), str(self.cntErrClass(i)), mainstr)  
        # res=re.findall(r"\$Class\[(-*\d)]",mainstr)
        # for i in res:
            # mainstr=re.sub(r"\$Class\[-*{0}]".format(int(i)), str([int(self.cond[i][0]) for i in range(len(self.strlist))].count(int(num))), mainstr)  
        
        return mainstr
    def logPrintSet(self,i,cond):
        # print(cond[i][1][-1])
        if(cond[i]["option"]=="full"):
            mainstr=self.setErrStr(self.strlist)
            print(mainstr)
        if(cond[i]["option"]=="lasterr"):
            mainstr=self.setErrStr([self.lasterr()])
            print(mainstr)
        if(cond[i]["option"]=="firsterr"):
            mainstr=self.setErrStr([self.firsterr()])
            print(mainstr)
        if(cond[i]["option"]=="none"):
            print("\n")
        
    def checkConditions(self,cond):
        for i in range(len(cond)):
            result1 = re.split(' +', cond[i]["condition"])
            if len(result1)==1:
                if int(cond[i]["condition"]) in [self.strlist[i][1] for i in range(len(self.strlist))]:
                    printd(f'find error class {cond[i]["condition"]} in errorlist')
                    printd2(self.replaceKeywords(cond[i]["pstring"][1]).replace(r"\n","\n"))
                    # printd(cond[i][1])
                    self.logPrintSet(i,cond)
            if len(result1)>1:
                cnt=int(self.replaceKeywords(result1[0]))
                if result1[1] == '>' and cnt > int(result1[2]): 
                    printd2(cnt,">",result1[2])
                    print(self.replaceKeywords(cond[i]["pstring"][1]).replace(r"\n","\n"))
                    mainstr=self.setErrStr(self.strlist)
                    self.logPrintSet(i,cond)
                
                if result1[1] == '<' and cnt < int(result1[2]): 
                    printd2(cnt,"<",result1[2])
                    print(self.replaceKeywords(cond[i]["pstring"][1]).replace(r"\n","\n"))
                    mainstr=self.setErrStr(self.strlist)
                    self.logPrintSet(i,cond)
                
    def setErrStr(self,stringlist,type='console',id=''):
        mainstr=""
        if isinstance(stringlist, str):
            stringlist=[stringlist]
        for str1 in stringlist:
            for config in self.confCl:
                if str1["class"] == config["class"] and config["type"] == 'console' and id=='':
                    if(config["text"] == ""):
                        mainstr+=self.replaceKeywords(config["text"],str1)+"\n";
                    else:
                        mainstr+=self.replaceKeywords("\n$txterr",str1)+"\n";
        return mainstr

class SearchEngine:
    """Класс предназначен для поиска по ключевым словам в файле журнала"""
    def __init__(self,confRE,confCl,file="",fileurl=""):
        self.confRE,self.confCl=confRE,confCl
        self.inp1=InputManager()
        self.logfile=self.inp1.getLogfile(file,fileurl)
        if self.logfile == "":
            exit("Error: file not found")
        
    def startFind(self):
        start_time = time.time()
        result=list()
        self.inp1.openFile(self.logfile)
        while True:
            fl,line=self.inp1.nextLine()
            if fl:
                break
            for regex in self.confRE:
                # if 1:
                if regex["keystr"] in line:
                    printd2("\nfline:",re.findall(r"^\[ *\d*s] (.*)",line)[0])
                    for j in range(0,len(regex["regexlist"])):
                        # print("asasda",len(regex["regexlist"]))
                        str1=re.findall(r"^\[ *\d*s] (.*)",line)[0].rstrip("\n") # строка без начального " [****] " и конечного "\n"
                        match=re.findall(regex["regexlist"][j]["regex"],str1)
                        if match:
                            printd2("\nline: ", str1)
                            printd2("regex:", regex["regexlist"][j]["regex"])
                            printd2("match:", match)
                            result.append({"string":str1,"class":regex["regexlist"][j]["class"],"match":match})
                            break
        printd("\nПоиск завершен за",time.time() - start_time, "секунд"," \nКоличество строк в файле:",self.inp1.strnum)
        return result
    
    
    
class InputManager:
    """
    Класс предназначен для управления вводом из файлов. 
    Экземпляр класса может открывать только один файл за раз.
    """
    strnum=0
    def openFile(self,file):
        self.file1 = open(file, "r",encoding='utf-8')

    def closeFile(self):
        self.file1.close
        
    def download_file(self,url): 
        local_filename = url.split('/')[-1] 
        with requests.get(url, stream=True) as r: 
            with open(local_filename, 'wb') as f: 
                shutil.copyfileobj(r.raw, f) 
        return local_filename
    def getLogfile(self,file="",fileurl=""):
        if fileurl != "":
            return self.download_file(fileurl)
        if file != "":
            return file
        #file = os.environ["userprofile"]+r"\Downloads\_log.txt"
        file = r"./_log.txt"
        return ""
        #return file
        
    def nextLine(self):
        flagEOF=0
        if not self.file1:
            print("ERROR: No file opend")
            return 0,""
        while True:
            self.line = self.file1.readline()
            self.strnum+=1
            if not self.line:
                flagEOF=1
                return flagEOF, ""
                break
            return flagEOF, self.line
    
    def getPos(self):
        return file1.tell()
    
    def getPos(self):
        file1.seek(pos)
    def JSONload(self,filename):
        with open(filename, "r") as read_file:
            data = json.load(read_file)
            # print(data)
        return data
    def getConfigs(self):
        configArr1=list()
        currArr=-1
        
        # Ввод regex.config
        with open("regex.json", "r") as read_file:
            configArr1 = json.load(read_file)
            if configArr1:
                        # Ввод classifier.config
                with open("classifier.json", "r") as read_file:
                    configArr2 = json.load(read_file)
                # print(data)
                if configArr2:
                    return configArr1,configArr2["classes"],configArr2["conditions"]
        conf1=InputManager()
        conf1.openFile("regex.config")
        fl,line = conf1.nextLine()
        if fl:
            return 0
        result = re.split(r' ', line)
        delimiter=result[0]
        comm=result[1]
        if not delimiter:
            exit()
        while True:
            fl,line=conf1.nextLine()
            if fl:
                break
            if line[0]==comm:
                continue
            result = re.split(delimiter, line)
            # print(result)
            if re.match(r'\s', result[0]):
                currArr=currArr+1
                configArr1.append([])
                configArr1[currArr].append(result[1])
            else:
                configArr1[currArr].append([result[1],int(result[2])])
        

        
        conditional=list()
        conf1.openFile("classifier.config")
        configArr2=list()
        conditional=list()
        cnt=-1
        while True:
            fl,line=conf1.nextLine()
            if fl:
                break
            if line[0]=="\n":
                continue
            while line[0:2]=="if":
                cnt+=1
                conditional.append([line[3:-2]])
                fl,line=conf1.nextLine()
                if fl:
                    break
                while line[0] == "\t":
                    result1 = re.split('#', line[1:-1])
                    conditional[cnt].append(result1)
                    fl,line=conf1.nextLine()
                    if fl:
                        break
                    # conditional[cnt].append(line)
                    
            
            result1 = re.split('#', line)
            fl,line2=conf1.nextLine()
            if fl:
                break
            try:
                configArr2.append([[int(result1[0]),result1[1],result1[2],result1[3]],line2])
            except Exception:
                print("\nUnable to parse around:\n",line)
                return 0,0,0
        # printd(configArr2)
        return configArr1,configArr2,conditional

if __name__ == "__main__":
    main()