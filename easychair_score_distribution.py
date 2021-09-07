# Reads conference data exported from EasyChair and produces statistics on score distribution.
# Copyright 2021 Rasmus Pagh
# MIT License

import sys
import io
import os.path
import zipfile
import csv
import datetime
import pathlib

# Conference specific values:
conference_name = "ESA 2021"
scores = [3, 2, 1, 0, -1, -2]
accept_scores = [3, 2, 1]
topics_string = 'Topics' # Indicator for topics in submission_field_value.csv, assuming that there is a list of author-specified topics for each paper

if len(sys.argv) != 2:
    print("Usage: python3 easychair_score_distribution.py <zipfile>")
    sys.exit()

filename = sys.argv[1]
if not os.path.exists(filename):
    print(f"File {filename} not found")
    sys.exit()

fname = pathlib.Path(filename)
mtime = datetime.datetime.fromtimestamp(fname.stat().st_mtime)

archive = zipfile.ZipFile(filename,'r')
csvfile_bytes = archive.open('review.csv')
csvfile_text  = io.TextIOWrapper(csvfile_bytes, encoding='utf8', newline='\n')
csvreader = csv.reader(csvfile_text, delimiter=',', quotechar='"')
reviews = []
for row in csvreader:
    score_parsed = row[7].replace(': ', '\n').split('\n')
    submission, member, score, confidence = int(row[1]), row[3], int(score_parsed[1]), int(score_parsed[3])
    reviews.append((submission, member, score, confidence))

archive = zipfile.ZipFile(filename,'r')
csvfile_bytes = archive.open('submission_field_value.csv')
csvfile_text  = io.TextIOWrapper(csvfile_bytes, encoding='utf8', newline='\n')
csvreader = csv.reader(csvfile_text, delimiter=',', quotechar='"')
topics = []
for row in csvreader:
    if row[2] == topics_string:
        submission, topic = int(row[0]), row[3]
        topics.append((submission, topic))

# Map topics to papers, and count #occurrences for each topic
submission2topics = {}
topic2count = {}
for (submission, topiclist) in topics:
    for topic in topiclist.split(", "):
        if submission not in submission2topics:
            submission2topics[submission] = []
        submission2topics[submission].append(topic)   
        if topic not in topic2count:
            topic2count[topic] = 0
        topic2count[topic] += 1


# Analysis
def scoretable(x2score):
    new_scoretable = {}
    for x in x2score:
        for score in scores:
            new_scoretable[(x,score)] = 0
    for score in scores:
        new_scoretable[('Total',score)] = 0
    for x in x2score:
        for score in x2score[x]:
            new_scoretable[(x,score)] += 1
            new_scoretable[('Total',score)] += 1
    return new_scoretable

member2score = {}
topic2score = {}
submission2score = {}

for (submission, member, score, confidence) in reviews:
    if member not in member2score:
        member2score[member] = []
    if submission not in submission2score:
        submission2score[submission] = []
    member2score[member].append(score)
    submission2score[submission].append(score)
    if submission in submission2topics:
        for topic in submission2topics[submission]:
            if topic not in topic2score:
                topic2score[topic] = []
            topic2score[topic].append(score)        

member2batchscore = {}
for (submission, member, score, confidence) in reviews:
    if member not in member2batchscore:
        member2batchscore[member] = []
    member2batchscore[member].extend(submission2score[submission])

memberscores = scoretable(member2score)
topicscores = scoretable(topic2score)
batchscores = scoretable(member2batchscore)

# Statistics on score per PC member and per topic
def sorted_table(x2score, scoretable):
    table = []
    total = 0
    for x in x2score:
        acceptrate = round(sum([scoretable[(x, score)] for score in accept_scores]) / sum([scoretable[(x, score)] for score in scores]),2)
        submission_number = sum([scoretable[(x, score)] for score in scores])
        if x!='':
            table.append( [acceptrate, submission_number, x] + [scoretable[(x, score)] for score in scores] )
            for score in scores:
                total += scoretable[(x, score)]
    table.sort()
    x = 'Total'
    acceptrate = round(sum([scoretable[(x, score)] for score in accept_scores]) / sum([scoretable[(x, score)] for score in scores]),2)
    table.append([acceptrate, '-', x] + [scoretable[(x, score)] for score in scores])
    table.append(['-', '-', 'Total percentage'] + [int(100 * scoretable[(x, score)]/total) for score in scores])    
    return table

def html_table(table):
    result = ""
    for row in table:
        result += '<tr>'
        for i in row:
            result += f'<td>{i}</td>'
        result += '</tr>'
    return result


with open('scores.html', 'w') as f:
    print("""<html><head>
    <meta charset="UTF-8">
    <style>
        table, th, td {
        border: 1px solid black;
        border-collapse: collapse;
        }
    </style>
    </head>
    <body>""", file=f)
    print(f"<h1> {conference_name} score statistics</h1>", file=f)
    print(f"Last update: {mtime.isoformat()} CEST", file=f)  
    print("<h2>Score distribution by PC member</h2>", file=f)
    print("<table>", file=f)    
    print("<tr><th>Accept rate</th><th>Reviews</th><th>Name</th><th>+3</th><th>+2</th><th>+1</th><th>0</th><th>-1</th><th>-2</th></tr>", file=f)
    print(html_table(sorted_table(member2score, memberscores)), file=f)
    print("</table><br/><hl/><br/>", file=f)
    print("<h2>Score distribution for batch, by PC member</h2>", file=f)
    print("<p>This is the combined distribution of scores for the batch of papers that this PC member reviewed (including their own scores)</p>", file=f)
    print("<table>", file=f)    
    print("<tr><th>Batch accept rate</th><th>Reviews in batch</th><th>Name</th><th>+3</th><th>+2</th><th>+1</th><th>0</th><th>-1</th><th>-2</th></tr>", file=f)
    print(html_table(sorted_table(member2score, batchscores)), file=f)
    print("</table><br/><hl/><br/>", file=f)
    print("<h2>Score distribution by area</h2>", file=f)
    if len(topic2score) == 0:
        print("<p>No topic information found in conference data (file submission_field_value.csv)</p>", file=f)
    else:
        print("<table>", file=f)    
        print("<tr><th>Accept rate</th><th>Scores</th><th>Area</th><th>+3</th><th>+2</th><th>+1</th><th>0</th><th>-1</th><th>-2</th></tr>", file=f)
        print(html_table(sorted_table(topic2score, topicscores)), file=f)
        print("</table>", file=f)
    print("</body></html>", file=f)
