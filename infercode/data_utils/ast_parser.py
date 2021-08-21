from os import path
from .vocabulary import Vocabulary
from .language_util import LanguageUtil
from tree_sitter import Language, Parser
from pathlib import Path
import glob, os
import numpy as np

class ASTParser():
    import logging
    LOGGER = logging.getLogger('ASTParser')
    def __init__(self, language=None):


        # ------------ To initialize for the treesitter parser ------------
        home = str(Path.home())
        cd = os.getcwd()
        os.chdir(path.join(home, ".tree-sitter", "bin"))
        self.Languages = {}
        for file in glob.glob("*.so"):
          try:
            lang = os.path.splitext(file)[0]
            self.Languages[lang] = Language(path.join(home, ".tree-sitter", "bin", file), lang)
          except:
            print("An exception occurred to {}".format(lang))
        os.chdir(cd)
        self.parser = Parser()
        
        self.language = language
        if self.language == None:
            self.LOGGER.info("Cannot find language configuration, using java parser to parse the code into AST")
            self.language = "java"

        lang = self.Languages.get(self.language)
        self.parser.set_language(lang)
        # -----------------------------------------------------------------

       
    def parse_with_language(self, code_snippet, language):
        lang = self.Languages.get(language)
        self.parser.set_language(lang)
        return self.parser.parse(code_snippet)

    def parse(self, code_snippet):
        return self.parser.parse(code_snippet)
    
    def set_language(self, language):
        lang = self.Languages.get(language)
        self.parser.set_language(lang)