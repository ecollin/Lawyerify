CREATE DATABASE thesaurus;

USE thesaurus;

/* Strictly speaking words table also contains phrases, but conceptually they are
 treated the same and all other names seemed less intuitive. */
CREATE TABLE words (
    word_id int NOT NULL AUTO_INCREMENT,
    word varchar(100) NOT NULL,
    UNIQUE(word),
    PRIMARY KEY(word_id) 
);

CREATE TABLE parts_of_speech (
	pos_id int NOT NULL AUTO_INCREMENT,
	pos varchar(20) NOT NULL,
	UNIQUE (pos),
	PRIMARY KEY (pos_id)
);

CREATE TABLE meanings (
	meaning_id int NOT NULL AUTO_INCREMENT,
	meaning varchar(100) NOT NULL,
    pos_id int NOT NULL,
    word_id int NOT NULL,
    UNIQUE (meaning),
    FOREIGN KEY (pos_id) REFERENCES parts_of_speech(pos_id),
    FOREIGN KEY (word_id) REFERENCES words(word_id),
	PRIMARY KEY (meaning_id)
);

/* Used for synonyms from thesaurus.com that have meaning data. */
CREATE TABLE syn_map_meaning (
    meaning_id int NOT NULL,
    syn_id int NOT NULL,
    similarity_rating tinyint,
    FOREIGN KEY (meaning_id) REFERENCES meanings(meaning_id),
    FOREIGN KEY (syn_id) REFERENCES words(word_id),
    PRIMARY KEY (meaning_id, syn_id)
);

/* Used for synonyms from words.bighugelabs.com without meaning data */
CREATE TABLE syn_map_pos (
    primary_word_id int NOT NULL,
    syn_id int NOT NULL,
    pos_id int NOT NULL,
    FOREIGN KEY (primary_word_id) REFERENCES words(word_id),
    FOREIGN KEY (syn_id) REFERENCES words(word_id),
    FOREIGN KEY (pos_id) REFERENCES parts_of_speech(pos_id),
    PRIMARY KEY (primary_word_id, syn_id, pos_id)
);
