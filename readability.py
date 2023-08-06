import math

import pyphen  # https://tug.org/docs/liang/
import re
import string
from nltk.tokenize import sent_tokenize, word_tokenize


def map_score(value, min_value, max_value, min_score=1, max_score=6):
    """
    Map a value from a range to another range.

    :param value:
    :param min_value:
    :param max_value:
    :param min_score:
    :param max_score:
    :return:
    """
    span_value = max_value - min_value
    span_score = max_score - min_score
    scaled_value = float(value - min_value) / float(span_value)
    return min_score + (scaled_value * span_score)


# https://stackoverflow.com/a/52668721
def process_text(text):
    """
    Remove punctuation and change to whitespace, then strip whitespace.

    :param text: Input text
    :return: Processed text
    """
    return text.translate(str.maketrans(string.punctuation, ' ' * len(string.punctuation))) \
        .replace(' ' * 4, ' ').replace(' ' * 3, ' ').replace(' ' * 2, ' ').strip()


def get_num_syllables(text, lang):
    """
    Return the number of syllables in a text.
    """
    # Create ney Pyphen translator
    dic = pyphen.Pyphen(lang=lang)

    total = 0
    # For each processed word, get number of syllables
    for word in word_tokenize(text):
        # If it is indeed a word
        if any(letter in text for letter in string.ascii_letters):
            total += len(list(dic.iterate(word))) + 1

    return total


def get_num_words(text):
    """
    Return the words of sentences in a text.
    """
    return len(word_tokenize(text))


def get_num_poly(text, lang):
    """
    Return the number of words with 3 or more syllables (polysyllabic word) in a text.
    """
    # Create ney Pyphen translator
    dic = pyphen.Pyphen(lang=lang)

    total = 0
    # For each processed word, get number of syllables
    for word in word_tokenize(text):
        # If it is indeed a word
        if any(letter in text for letter in string.ascii_letters):
            if len(list(dic.iterate(word))) + 1 >= 3:
                total += 1

    return total


def get_num_sentences(text):
    """
    Return the number of sentences in a text.
    """
    return len(sent_tokenize(text))


def stats(text, lang):
    """
    :return: num_char, num_syllables, num_words, num_poly, num_sentences
    """
    try:
        num_char = len(text)
        num_syllables = get_num_syllables(text, lang)
        num_words = get_num_words(text)
        num_poly = 0
        num_sentences = get_num_sentences(text)
        return num_char, num_syllables, num_words, num_poly, num_sentences
    except LookupError:
        import nltk
        nltk.download('punkt')
        return stats(text, lang)


def flesch(text, lang, norm=True):
    # https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests
    _, num_syllables, num_words, _, num_sentences = stats(text, lang)
    fres = 206.835 - 1.015 * (num_words / num_sentences) - 84.6 * (num_syllables / num_words)
    return map_score(fres, 0, 100) if norm else fres


def flesch_kincaid(text, lang, norm=True):
    # https://en.wikipedia.org/wiki/Flesch%E2%80%93Kincaid_readability_tests
    _, num_syllables, num_words, _, num_sentences = stats(text, lang)
    fkgl = 0.39 * (num_words / num_sentences) + 11.8 * (num_syllables / num_words) - 15.59
    return map_score(fkgl, 1, 15) if norm else fkgl


def automated_readability_index(text, lang, norm=True):
    # https://en.wikipedia.org/wiki/Automated_readability_index
    num_char, _, num_words, _, num_sentences = stats(text, lang)
    ari = 4.71 * (num_char / num_words) + 0.5 * (num_words / num_sentences) - 21.43
    return map_score(ari, 1, 15) if norm else ari


def smog_grade(text, lang, norm=True):
    # https://en.wikipedia.org/wiki/SMOG
    _, _, _, num_poly, num_sentences = stats(text, lang)
    smog = 1.043 * math.sqrt(num_poly * (30 / num_sentences)) + 3.1291
    return map_score(smog, 1, 15) if norm else smog


def coleman_liau_index(text, lang, norm=True):
    # https://en.wikipedia.org/wiki/Coleman%E2%80%93Liau_index
    num_char, _, num_words, _, num_sentences = stats(text, lang)
    cli = 5.88 * (num_char / num_words) - 2.96 * (num_sentences / num_words) - 15.8
    return map_score(cli, 1, 15) if norm else cli


def gunning_fog_index(text, lang, norm=True):
    # https://en.wikipedia.org/wiki/Gunning_fog_index
    _, _, num_words, num_poly, num_sentences = stats(text, lang)
    gfi = 0.4 * ((num_words / num_sentences) + 100 * (num_poly / num_words))
    return map_score(gfi, 1, 15) if norm else gfi
