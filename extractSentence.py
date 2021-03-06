__author__ = 'zhangye'
#this file predicts relationship and its level in sentence level
import xlrd
import re
import os
from nltk.tokenize import sent_tokenize
from sklearn.linear_model import LogisticRegression
from sklearn.grid_search import GridSearchCV
from sklearn import cross_validation
from sklearn.feature_extraction.text import CountVectorizer
import codecs
import numpy as np
import unicodedata
import pickle
from textblob import TextBlob
from sklearn.metrics import f1_score
from operator import itemgetter
from sklearn import linear_model
from nltk.corpus import stopwords
from sets import Set
#stop words
stops = set(stopwords.words('english'))
def convert(str1):
    if(type(str1) is unicode):
        str1 = str1.encode('ascii','ignore')
        str1 = str1.strip('.')
        str1 = str1.lower()
        str1.replace("see above","")
        str1.replace("as above","")
        str1 = str(TextBlob(str1).correct())
        temp =  re.split(r'\.\. \.\.|,|/',str1)
        return [a.strip() for a in temp if (a.strip().isspace()==False and a)]
    elif(type(str1) is float):
        return str(str1)

def remove_punct(term):
    return " ".join(list(filter((lambda x: x not in stops),list(TextBlob(term).correct().words))))


sentences = []
y = []
threshold = 0
level = []

#write postiive sentences to sen_file
#sen_file = open("sentence.txt","w")
ignore = ["posted on","word count","sentence","title"]
#d = enchant.Dict("en_US")
dic = {}

def is_ignore(text):
    for str in ignore:
        if(str in text):
            return 1
    return 0
Chambers_sentence = "Chambers_sen/"
j = 1
for file_name in os.listdir("1. excel files"):
    if file_name.endswith(".xls"):
        #print file_name
        book = xlrd.open_workbook("1. excel files/"+file_name)
        first_sheet = book.sheet_by_index(0)
        relation = first_sheet.cell(124,5).value
        code =  first_sheet.cell(125,5).value
        terms = first_sheet.cell(129,5).value

        if(terms and terms!=-9):
            print terms
            terms = convert(terms)
            print terms
            for i in terms:
                    if("as above" in i or i.isspace() or not i or "see above" in i):
                        continue
                    # i is one relationship term, could be a single word or phrase
                    cur_term = i.strip()
                    cur_term = remove_punct(i)
                    #print "finish processing relation terms for file "+file_name + i
                    if(dic.has_key(cur_term)):
                        dic[cur_term].append(file_name)
                    else:
                        dic[cur_term] = [file_name]

        filename = file_name.split('.')[0]
        f = codecs.open("5. Press releases/"+filename[:-2]+".txt",'r',encoding='utf-8')
        text = f.readlines()
        text = [i.encode('ascii','ignore') for i in text]
        writeFile = open(Chambers_sentence+str(j),'wb')

        #check each line  whether contains relationship terms
        for line in text:
            original = line
            if(line.strip().isspace()):
                continue
            line = line.lower().strip()
            if(is_ignore(line)):
                continue
            sentences.append(line)
            #code is equal to zero, no relationship
            if(code<=threshold):
                #level.append(0)
                y.append(0)
                continue
            #code is non zero,
            #primary relationship sentence
            if relation.encode('ascii','ignore').lower() in line:
                level.append(code)
                y.append(1)
                #print "sen "+line
                #sen_file.write(file_name+" "+line+"\n")
            #following sentences stating relationship
            elif(terms is not None and terms!=-9):
                flag = 0
                for i in terms:
                    if("as above" in i or i.isspace() or not i or "see above" in i):
                        continue
                    if i in line:
                        y.append(1)
                        flag = 1
                        level.append(code)
                        break
                if(flag==0):
                    y.append(0)
            else:
                y.append(0)

            #write the current line with the label into the sentences directory
            if line:
                writeFile.write(line+"\t"+str(y[-1])+"\n")
        writeFile.close()
        j+=1

#stores the dictionary
pickle.dump(dic,open("relation_terms","wb"))
parameters = [1000,100,10,1, .1, .01, .001,0.0001,0.00001]
level = np.array(level)
threshold_index = np.nonzero(level>3)
y1 = np.zeros(len(level))
y1[threshold_index] = 1
kf1 = cross_validation.StratifiedKFold(y1,n_folds=5,shuffle=True)
lr1 = LogisticRegression(penalty="l2",fit_intercept=True)
clf1 = GridSearchCV(lr1, parameters, scoring='f1',cv=kf1)
#clf1.fit(relation_sentence,y1)
print clf1.grid_scores_


#sen_file.close()
labeled_sen = []
labeled_y = []

#read the Oxford press release labeled by the dictionary terms
for file_name in os.listdir("PR_Oxford_Sentence"):
    if(not file_name.endswith(".txt")):
        continue
    temp = open("PR_Oxford_Sentence/"+file_name)
    for line in temp:
        line = line.strip()
        label = int(line[-1].strip())
        sen = line[:-1]
        labeled_sen.append(sen.strip())
        labeled_y.append(label)
    temp.close()

for file_name in os.listdir("PR_Harvard"):
    if(not file_name.endswith(".txt")):
        continue
    temp = open("PR_Harvard/"+file_name)
    for line in temp:
        line = line.strip()
        label = int(line[-1].strip())
        sen = line[:-1]
        labeled_sen.append(sen.strip())
        labeled_y.append(label)
    temp.close()

vectorizer = CountVectorizer(ngram_range=(1), stop_words="english",
                                    min_df=1,
                                    #token_pattern=r"(?u)[a-zA-Z0-9-_/*][a-zA-Z0-9-_/*]+\b",
                                    binary=False)
#sentences = vectorizer.fit_transform(sentences)
y = np.array(y)
#relation_index = np.nonzero(y)
#relation_sentence = sentences[relation_index]
kf = cross_validation.KFold(len(y),n_folds=5,shuffle=True)
lr = LogisticRegression(penalty="l2", fit_intercept=True,class_weight='auto')


#labeled_sen = []
#labeled_y = []
for p in parameters:
    #lr = LogisticRegression(penalty="l2", fit_intercept=True,class_weight='auto',C=p)
    lr = linear_model.SGDClassifier(loss='log',penalty='l2',fit_intercept=True,class_weight='auto',alpha=p,n_iter=50)
    mean = []
    for train_index, test_index in kf:
        train_sentence = list(itemgetter(*train_index)(sentences)) + labeled_sen
        train_label = list(itemgetter(*train_index)(y)) + labeled_y
        test_sentence = list(itemgetter(*test_index)(sentences))
        train_sentence = vectorizer.fit_transform(train_sentence)
        test_sentence = vectorizer.transform(test_sentence)
        test_label = list(itemgetter(*test_index)(y))
        ins_weight = np.ones(len(train_index))
        ins_weight = np.concatenate((ins_weight,np.ones(len(labeled_y))*0.3))
        lr.fit(train_sentence,np.array(train_label),sample_weight=ins_weight)
        predict = lr.predict(test_sentence)
        f1 = f1_score(test_label,predict)
        mean.append(f1)
    print(str(p)+" "+str(sum(mean)/len(mean))+"\n")

clf0 = GridSearchCV(lr, parameters, scoring='f1',cv=kf)
print "fitting model..."
clf0.fit(sentences,y)
print clf0.grid_scores_







