import requests
import urllib.request
import time
from bs4 import BeautifulSoup   
import re
import json
import mysql.connector as mysql
from sys import exit

"""
Used to scrape thesaurus.com for synonyms of words parsed from a file and add them
to the local thesaurus SQL database.
"""

def scrape_syn_data(word, log_file='log.txt'):
    """
    Scrapes data from the thesuarus.com page for the given word and returns a list holding
    information on each definition of the word and the synonyms for it

    ARGUMENTS:
    word - the word to scrape data on

    RETURNS: 
    Returns data in the following form (the word being scraped is put in this case)
    [
         {'definition': 'position', 'pos': 'verb', 'word': 'put', 'synonyms': 
            [
               {'similarity': '100','term': 'bring'}, ... (other synonym dicts)
            ]
         }, ... (other dictionaries holding information on other definitions of
                          of the word)
       ] 
    """
    url = r'https://www.thesaurus.com/browse/' + word
    response = requests.get(url)
    if response.status_code != 200:
        with open(log_file, 'a') as log:
            log.write(f'FOR WORD {word}: got status code {response.status_code}')
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    # thesaurus.com pages have a script tag which just sets window.INITIAL_STATE
    # to a JSON object. We want to parse for this object.
    # We will search for pattern only within a script tag so the .* will not cause it
    # to go on forever
    pattern = re.compile(r'INITIAL_STATE = (\{.*\});', re.DOTALL)
    script = soup.find('script', text=pattern)
    if not script:
        with open(log_file, 'a') as log:
            log.write(f'FOR WORD {word}: Failed to find initial state script tag')
        return None
    initial_state_str = pattern.search(script.string).group(1)
    # the parsed string was JS and used "undefined" which is not valid JSON
    initial_state_str = initial_state_str.replace('undefined', 'null')
    parsed = json.loads(initial_state_str)
    # def tabs is a list of dictionaries holding information on a particular definition of 
    # given word. Each definition has a field synonyms containing a list of synonym dicts
    def_tabs = parsed['searchData']['tunaApiData']['posTabs']
    # cleaned_def_tabs will be a list of same format as def_tabs but will remove unnecessary
    # keys from the definition dict and its synonyms dicts.
    cleaned_def_tabs = []
    definition_fields = ['definition', 'pos']
    syn_fields = ['similarity', 'term']
    for definition_dict in def_tabs:
        dict_copy = {k : definition_dict[k] for k in definition_fields}
        # Store the word that we are looking at a definition + synonyms for
        dict_copy['word'] = word
        syns_copy = []
        for syn in definition_dict['synonyms']:
            syn_copy = {k : syn[k] for k in syn_fields}
            syns_copy.append(syn_copy)
        dict_copy['synonyms'] = syns_copy
        cleaned_def_tabs.append(dict_copy)
    
    return cleaned_def_tabs

def get_words_to_scrape(file_path, num_words, delete=True, log_file='log.txt'):
    """
    Takes the path to a file that holds on each line a word we will scrape for synonyms.
    Ignores lines starting with #. 

    PARAMETERS:
    file_path : the path at which the file is. File should contain new word in each line
    and optionally comment lines starting with #.
    delete : If True, after a word is read, its line will be removed from the file.
    Otherwise the file will be untouched. Comments will be deleted as well if they are
    between the start of file and the deleted lines.
    log_file : A file to log errors to. If None errors will not be logged.

    RETURNS:
    If file_path holds a properly formatted file, word on the first line will be returned.
    Otherwise, or if the file is empty, None will be returned.
    """
    with open(file_path, 'r') as filein:
        data = filein.read().splitlines(True)

    if len(data) == 0:
        if log_file:
            with open(log_file, 'a') as log:
                log.write('get_word_to_scrape found empty file')
        return None

    words = []
    curr_line = 0
    while len(words) < num_words and curr_line < len(data):
        if not data[curr_line].startswith('#'):
            words.append(data[curr_line].strip())
        curr_line += 1

    if delete:
        with open(file_path, 'w') as fileout:
            fileout.writelines(data[curr_line + 1:])

    return words


def add_syns_data_to_db(cursor, syns_data):
    """
    Takes a db cursor and a syns_data list and adds the list to the thesaurus database.
    Assumes that the thesuarus used is "thesuarus.com".

    Parameters:
    cursor - db cursor where "USE thesuarus;" has been executed
    syns_data: a list holding lists of the following form (as returned by the scrape)
    function above):
    [
        {'definition': 'position', 'pos': 'verb', 'word': 'put', 'synonyms': 
            [
            {'similarity': '100','term': 'bring'}, ... (other synonym dicts)
            ]
        }, ... (other dictionaries holding information on other definitions of
                        of the word)
    ] 
    Returns:
    None
    """
    # Short internal helper to insert value into column of table
    # if it doesn't exist. Assumes column is only required column of table.
    def insert_if_not_exists(table, column, value):
        if isinstance(value, str):
            value = '"' + value + '"'
        cursor.execute(f'SELECT * FROM {table} WHERE {column}={value};')
        # Need to fetch result to execute further commands
        cursor.fetchone()
        if cursor.rowcount <= 0: 
            cursor.execute(f'INSERT INTO {table} ({column}) VALUES ({value});')
        
    for meaning_dict in syns_data:
        # TODO: Consider what to do if error occurs after adding the new meaning.
        pos = meaning_dict['pos']   
        word = meaning_dict['word']
        insert_if_not_exists('parts_of_speech', 'pos', pos)
        insert_if_not_exists('words', 'word', word)

        cursor.execute(f'SELECT pos_id FROM parts_of_speech WHERE pos="{pos}"')
        pos_id = cursor.fetchone()[0]
        cursor.execute(f'SELECT word_id FROM words WHERE word="{word}"')
        word_id = cursor.fetchone()[0]

        meaning = meaning_dict['definition']
        
        meaning_insert_str = ('INSERT INTO meanings (meaning, pos_id, word_id) '
            f'VALUES ("{meaning}", {pos_id}, {word_id});')
        cursor.execute(meaning_insert_str)

        cursor.execute(f'SELECT meaning_id FROM meanings WHERE meaning="{meaning}"')
        meaning_id = cursor.fetchone()[0]

        for synonym in meaning_dict['synonyms']:
            similarity = synonym['similarity']
            syn = synonym['term']
            insert_if_not_exists('words', 'word', syn)
            cursor.execute(f'SELECT word_id FROM words WHERE word="{syn}"')
            syn_id = cursor.fetchone()[0]
            syn_insert_str = ('INSERT INTO syn_map_meaning '
                '(meaning_id, syn_id, similarity_rating) '
                f'VALUES ({meaning_id}, {syn_id}, {similarity});')
            print(syn_insert_str)

            try:
                cursor.execute(syn_insert_str)
            except mysql.errors.ProgrammingError as err:
                print('About to insert: ', syn, word, pos, meaning, similarity)
                # For now I just reraise and let cron mail alert me to it
                raise err
            #else:
               # db.commit()



words_to_scrape = 1
wait_time = 10
# max_word_len is maximum num chars allowed by database for words/phrases
max_word_len = 100
log_file = 'log.txt'

words = get_words_to_scrape('test.txt', words_to_scrape, delete=True, log_file=log_file)
for (i, word) in enumerate(words):
    if len(word) > max_word_len:
        del words[i]

if not words:
    print('No words! Exiting')
    exit()

syns_datas = []
for (i, word) in enumerate(words):
    syns_data = scrape_syn_data(word)
    if syns_data:
        syns_datas.append(syns_data)
    # Dont make requests too often
    if i != len(words) - 1:
        time.sleep(wait_time)

if not syns_datas:
    print(f'No syns_datas scrapable for words {words}! Exiting')
    exit()


DB_user = 'root'
DB_pass = 'SEO'

db = mysql.connect(
    host="localhost",
    user=DB_user,
    passwd=DB_pass,
    auth_plugin='mysql_native_password',
    autocommit=True
)

cursor = db.cursor()

cursor.execute('USE thesaurus;')

for syns_data in syns_datas:
    add_syns_data_to_db(cursor, syns_data)

#db.commit()
cursor.close()
db.close()

