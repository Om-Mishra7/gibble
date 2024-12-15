from database import Database
import string


class Indexer:
    def __init__(self):
        self.db = Database()
        self.db.ensure_connection()

        self.analytics = {
            "number_of_pages": self.db.get_number_of_pages(),
            "pages_indexed": 0,
            "words_indexed": 0
        }

    def index_page(self, url, content):
        # Split the content into words and remove punctuation, whitespace, capitalization, common words, \n, and \r as well as words with less than 3 characters

        content = content["page_text"]

        words = content.split()
        words = [word.lower().strip(string.punctuation + string.whitespace) for word in words]

        # Remove common words

        common_words = ['a', 'an', 'the', 'and', 'or', 'but', 'about', 'above', 'after', 'along', 'amid', 'among', 'as', 'at', 'by', 'for', 'from', 'in', 'into', 'like', 'minus', 'near', 'of', 'off', 'on', 'onto', 'out', 'over', 'past', 'per', 'plus', 'since', 'till', 'to', 'under', 'until', 'up', 'via', 'vs', 'with', 'that', 'can', 'cannot', 'could', 'may', 'might', 'must', 'need', 'ought', 'shall', 'should', 'will', 'would', 'have', 'had', 'has', 'having', 'be', 'is', 'am', 'are', 'was', 'were', 'being', 'been', 'get', 'gets', 'got', 'gotten', 'getting', 'use', 'uses', 'used', 'using', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'first', 'second', 'third', 'many', 'much', 'more', 'most', 'other', 'another']

        words = [word for word in words if word not in common_words]

        # Remove empty strings

        words = [word for word in words if word]

        # Remove words with less than 3 characters

        words = [word for word in words if len(word) >= 3]

        self.analytics['words_indexed'] += len(words)

        self.db.insert_index(url, list(set(words)))


    def run(self):
        while True:
            url, content = self.db.get_page_to_index()
            if url is None:
                print("No more pages to index.")
                break
            
            self.index_page(url, content)

            self.db.mark_page_indexed(url)

            self.analytics['pages_indexed'] += 1

            print("\033[H\033[J")
            print("\nIndexer Statistics:")
            print(f"Pages to index: {self.analytics['number_of_pages']}")
            print(f"Pages indexed: {self.analytics['pages_indexed']}")
            print(f"Words indexed: {self.analytics['words_indexed']}")
            print(f"Percentage complete: {self.analytics['pages_indexed'] / self.analytics['number_of_pages'] * 100:.2f}%")


if __name__ == "__main__":
    indexer = Indexer()
    indexer.run()