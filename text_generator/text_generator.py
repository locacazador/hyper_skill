from collections import defaultdict, Counter
from typing import List, Tuple, Match
import random
import re


from nltk.util import ngrams


class Preprocessor:
    """Class to process data"""

    def __init__(self):
        """
        Create n_grams when initiating object. Count
        """

        path_input = input()
        self.tokens = []
        with open(path_input, 'r', encoding='utf-8') as f:
            data = f.read()
        self.tokens = data.split()
        tmp_dict = defaultdict(list)
        for val1, val2, val3 in ngrams(self.tokens, n=3):
            tmp_dict[val1 + ' ' + val2].append(val3)
        dataset_dict = {}
        for item in tmp_dict:
            counter = Counter(tmp_dict[item])
            dataset_dict[item] = counter
        self.data = dataset_dict

    def get_next_word(self, curr_word: str) -> Counter:
        """
        Get counter of word by previous in n_grams

        :param curr_word: word to search
        :Return Counter of word in n_grams
        """

        return self.data[curr_word]

    def generate_random(self) -> List[str]:
        """
        Generate random sentences by random start

        :Return Sentence found by algorithm of weighted counts in n_grams
        """

        while True:
            curr_iter = random.choice(list(self.data.keys()))
            if not self.str_endswith_punctuation(curr_iter) and curr_iter[0].isupper():
                break
        final_str = [*curr_iter.split()]
        is_capital = False
        while True:
            counter = self.get_next_word(curr_iter)
            next_iter, need_capital = self.find_in_counter(counter, capital=is_capital)
            is_capital = need_capital
            final_str.append(next_iter)
            if len(final_str) >= 5 and self.str_endswith_punctuation(next_iter):  # sentence more then 5 words add new
                break
            curr_iter = curr_iter.split(' ')[1] + ' ' + next_iter
        return final_str

    @staticmethod
    def find_in_counter(counter: Counter, capital: bool) -> Tuple[str, Match]:
        """
        Get next word. If @capital word must start with capital letter
        Else try to find the next word by weighted random choice in dataset

        :param counter: dataset of mapping counts_by_word
        :param capital: find word starting with capital letter
        :Return pair of next weighted random word and match object if it ends with punctuation sign
        """

        weights = [item for item in counter.values()]
        keys = list(counter.keys())
        while True:
            return_value = random.choices(keys, weights)[0]
            if capital:
                if not return_value[0].isupper():
                    return_value = None
            if return_value:
                return return_value, Preprocessor.str_endswith_punctuation(return_value)

    @staticmethod
    def str_endswith_punctuation(word: str) -> Match:
        """
        Check if @word ends with punctuation

        :param word: string to check
        """

        return re.match(r".+[.?!]", word)

    def generate_n_random_sentences(self, n=10) -> List[List[str]]:
        """
        Generate several random sentences by algorithm

        :param n: number of sentences to generate
        :Return list of sentences generated
        """

        return [self.generate_random() for _ in range(n)]


class Menu:
    """Class to interact with user"""

    @staticmethod
    def process_output(preprocessor_: Preprocessor) -> None:
        """
        Print the resulted sentences from @generate_n_random_sentences

        :param preprocessor_: object contains the dataset
        """

        for item in preprocessor_.generate_n_random_sentences():
            print(' '.join(item), end='\n')


if __name__ == '__main__':
    preprocessor = Preprocessor()
    Menu.process_output(preprocessor_=preprocessor)
