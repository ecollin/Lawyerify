CREATE DATABASE thesaurus;

USE thesaurus;

/* Strictly speaking words table also contains phrases, but conceptually they are
 treated the same and all other names seemed less intuitive. */
CREATE TABLE words (
    word varchar(100) NOT NULL,
    PRIMARY KEY(word) 
);

CREATE TABLE parts_of_speech (
	pos varchar(20) NOT NULL,
	PRIMARY KEY (pos    )
);

CREATE TABLE meanings (
    meaning varchar(100) NOT NULL,
    PRIMARY KEY (meaning)
);

/* Used for synonyms from thesaurus.com that have meaning data. */
CREATE TABLE syn_map_meaning (
    primary_word varchar(100) NOT NULL,
    meaning varchar(100) NOT NULL,
    pos varchar(20) NOT NULL,
    syn_word varchar(100) NOT NULL,
    similarity_rating tinyint,
    FOREIGN KEY (primary_word) REFERENCES words(word),
    FOREIGN KEY (meaning) REFERENCES meanings(meaning),
    FOREIGN KEY (pos) REFERENCES parts_of_speech(pos),
    FOREIGN KEY (syn_word) REFERENCES words(word),
    PRIMARY KEY (syn_word, primary_word, meaning, pos)
);