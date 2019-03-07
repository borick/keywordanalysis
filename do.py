import sys, re
import htmllib
import os
from operator import itemgetter
from BeautifulSoup import *

genFullText = False
commonWords = []
for line in open('ignored_words.txt','r'):    
    commonWords.append(re.sub(r"[^a-z]", "", line.lower()))

# functions
def unescape(s):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(s)
    return p.save_end()    

def _add_dict(token, keyword_dict):
    # do not add list of ignored words to our index.
    tokens = token.split()
    if (tokens[0] in commonWords):
        return        
    p = re.compile('[a-zA-Z]')
    # Do not add words with no alphanumerics in them.
    if (not p.match(token)):
        return        
        
    if keyword_dict.has_key(token):
        keyword_dict[token] += 1
    else:
        keyword_dict[token] = 1
        
def _strip_content(soup):
    # remove all comments
    comments = soup.findAll(text=lambda text:isinstance(text, Comment))
    [comment.extract() for comment in comments]
    # remove all declarations (doctype, etc.)
    declarations = soup.findAll(text=lambda text:isinstance(text, Declaration))
    [declaration.extract() for declaration in declarations]
        
def parse_tokens(my_string, keyword_dict, first_words):
    tokens = my_string.split()
    size = len(tokens)
    
    count = 0
    # Clean the tokens, first pass.
    for token in tokens:        
        tokens[count] = tokens[count].lower()
        tokens[count] = tokens[count].replace('.', u'')
        count += 1
        
    count = 0
    # Get the tokens, 2nd pass.
    for token in tokens:
        
        _add_dict(token, keyword_dict)
        
        if len(first_words) < 500:
            first_words.append(token)
        
        # 2 word combos
        if (count < size - 1):
            _add_dict(tokens[count] + u' ' + tokens[count+1], keyword_dict)
            
        # 3 word combos
        if (count < size - 2):
            _add_dict(tokens[count] + u' ' + tokens[count+1] + u' ' + tokens[count+2], keyword_dict)
            
        count += 1
        
def navigateTree(soup, keyword_dict, html_file):
                        
    if hasattr(soup, 'contents'):
        for content in soup.contents:
            navigateTree(content, keyword_dict, html_file)    
    else:
        p = re.compile('[a-zA-Z0-9]')
                
        if (p.match(soup)):
        
            # store the full text.
            if (not full_text_dict.has_key(html_file)):
                full_text_dict[html_file] = []            
            full_text_dict[html_file].append(unescape(soup))                
            
            parse_tokens(unescape(soup), keyword_dict[html_file], first_words_dict[html_file])
            
def parse_url(html_file, links=None):

    keyword_dict[html_file] = {}
    first_words_dict[html_file] = []
    
    try:    
        soup = BeautifulSoup(open(html_file))
    except IOError, e:
        return
    
    print "Parsing %s." % html_file    
    _strip_content(soup)

    titles = soup.findAll('title')
    title_dict[html_file] = titles[0].string
    
    navigateTree(soup, keyword_dict, html_file)
    
    if (links is not None):
        # get all links
        for link in soup.fetch('a'):    
            if link.has_key('href'):
                if link['href'] not in links:
                    links.append(link['href'])
    
def output_report(my_list, f):

    format = "        %-30s   %d\n"
    for key,value in my_list:        
        if value > 1:
            f.write(format % (key.encode('utf-8'), value))
    f.write(u"\n")

# command line args.
html_file = "index.html"
if len(sys.argv) > 1:
    html_file = sys.argv[1]
    
# init
links = []

# globals.
keyword_dict = {}
title_dict = {}
full_text_dict = {}
first_words_dict = {}

path_components = html_file.split("/")
base_path = ''
for ele in path_components[:-1]:
    base_path += ele + "/"

while(True):    
    parse_url(html_file, links)
    
    continue_flag = 0
    for link in links:
        new_file = base_path + link
        # remove the query portion, after the ?
        temp_parts = new_file.split('?')
        new_file = temp_parts[0]        
        # if we've already processed this file, then exit.
        if not keyword_dict.has_key(new_file):            
            continue_flag = 1
        else:
            continue
        parse_url(new_file, links)

    if (continue_flag == 0):
        break
        
print "Generating reports..."

reports_dir = "reports"
if not os.path.exists(reports_dir):
    os.makedirs(reports_dir)
    
if (genFullText):    
    for title_key in title_dict.keys():

        filename = str(title_dict[title_key])
        filename = re.sub(r"[^a-zA-Z0-9 ]", "", filename)
        
        # generate full text of the file.
        f = open(reports_dir + "/" + filename + '-full-text.txt', 'w')
        for text in full_text_dict[title_key]:
            f.write(text.encode('utf-8'))
            f.write(u"\n")
        f.close()        
    print "Total number of reports: %s" % len(title_dict.keys())

    
for keyword_key in keyword_dict.keys():

    if (title_dict.has_key(keyword_key)):
        filename = title_dict[keyword_key]
        filename = re.sub(r"[^a-zA-Z0-9 ]", "", filename)
        
        # generate keyword lists
        f = open(reports_dir + "/" + filename + '-keywords.txt', 'w')
        keyword_list = sorted(keyword_dict[keyword_key].items(), key=itemgetter(1), reverse=True)
        
        single_keywords_list = []
        double_keywords_list = []
        triple_keywords_list = []
        
        for key,value in keyword_list:
            keywords_split = key.split()
            if (len(keywords_split) == 3):
                triple_keywords_list.append((key,value))
            elif (len(keywords_split) == 2):
                double_keywords_list.append((key,value))
            else:
                single_keywords_list.append((key,value))
                
        f.write(u"Single keywords:\n\n")
        output_report(single_keywords_list, f)

        f.write(u"Groups-of-two keywords:\n\n")
        output_report(double_keywords_list, f)
        
        f.write(u"Groups-of-three keywords:\n\n")
        output_report(triple_keywords_list, f)
        
        f.write(u"First 500 words on page:\n\n")        
        for value in first_words_dict[keyword_key]:        
            f.write(value.encode('utf-8'))
            f.write(u" ")
        f.write(u"\n")
        f.close()        

print "Total number of reports: %s" % len(keyword_dict.keys())  
