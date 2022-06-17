import logging


class BookImporter:
    def process(self, filename, tags):
        logging.info("Importing book")
        logging.info("Filename: %s, tags: %s", filename, tags)
        raise NotImplementedError()
