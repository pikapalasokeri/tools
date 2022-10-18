#!/usr/bin/env python3
import argparse
import sys
import re
import os
import tempfile
import shutil
import contextlib

class Matcher:
    def __init__(self, inputArgs):
        searchStrings = inputArgs.search_strings
        for i, string in enumerate(searchStrings):
            searchStrings[i].strip("\"'")

            if inputArgs.ignore_case:
                searchStrings[i] = searchStrings[i].lower()

        self._rePatterns = []
        for string in searchStrings:
            self._rePatterns.append(re.compile(re.escape(string)))

        if inputArgs.replace is not None:
            self._replaceString = inputArgs.replace.strip("\"'")
        elif inputArgs.query_replace is not None:
            self._replaceString = inputArgs.query_replace.strip("\"'")
        else:
            self._replaceString = None

    def matchString(self, testString):
        matches = []

        replacedString = None
        if self._replaceString is not None:
            replacedString = re.sub(self._rePatterns[0], self._replaceString, testString)

        for pattern in self._rePatterns:
            newMatches = [x for x in pattern.finditer(testString)]
            if len(newMatches) == 0:
                return None, replacedString
            else:
                matches.extend(newMatches)

        return matches, replacedString

def intersects(list1, list2):
    return len(set(list1) & set(list2)) > 0

class Walker:
    def __init__(self, inputArgs, fileCallback):
        self._rootWalkDirectory = inputArgs.directory
        self._extensions = ["." + ext for ext in inputArgs.extensions.split(",")]
        self._excludeExtensions = ["." + ext for ext in inputArgs.exclude_extensions.split(",")]
        self._excludeDirectories = inputArgs.exclude_directories.split(",")
        self._fileCallback = fileCallback

    def walk(self):
        for root, dirs, files in os.walk(self._rootWalkDirectory):
            if self._skipDir(root):
                continue

            for f in files:
                _, fileExtension = os.path.splitext(f)
                if (fileExtension in self._extensions and
                    fileExtension not in self._excludeExtensions):
                    self._fileCallback(root, f)

    def _skipDir(self, directory):
        dirs = directory.split("/")
        return intersects(dirs, self._excludeDirectories)

class Printer:
    def __init__(self, colorizer):
        self._colorizer = colorizer

    def print(self, line, lineNumber, matches, root, fileName):
        print(" ".join(self._colorizer.colorize(root, fileName, lineNumber, line, matches)))

class Colors:
    COLOR_START     = "\033["
    GRAY            = COLOR_START + "1;30m"
    BLACK           = COLOR_START + "0;30m"
    BLUE            = COLOR_START + "0;34m"
    GREEN           = COLOR_START + "0;32m"
    CYAN            = COLOR_START + "0;36m"
    RED             = COLOR_START + "0;31m"
    PURPLE          = COLOR_START + "0;35m"
    BROWN           = COLOR_START + "0;33m"
    LIGHT_GRAY      = COLOR_START + "0;37m"
    DARK_GRAY       = COLOR_START + "1;30m"
    LIGHT_BLUE      = COLOR_START + "1;34m"
    LIGHT_GREEN     = COLOR_START + "1;32m"
    LIGHT_CYAN      = COLOR_START + "1;36m"
    LIGHT_RED       = COLOR_START + "1;31m"
    LIGHT_PURPLE    = COLOR_START + "1;35m"
    YELLOW          = COLOR_START + "1;33m"
    WHITE           = COLOR_START + "1;37m"
    NO_COLOR        = "\033[0m"

def matchSpanFunction(match):
    return match.span(0)

# Assume sorted, span1 <= span2
def overlaps(span1, span2):
    return span2[0] < span1[1]

def getUnionOfSpans(matches):
    result = []
    for match in sorted(matches, key = matchSpanFunction):
        span = match.span(0)
        if (len(result) > 0
            and overlaps(result[-1], match.span(0))):
            result[-1][1] = max(span[1], result[-1][1])
        else:
            result.append([span[0], span[1]])
    return result

class Colorizer:
    def __init__(self):
        pass

    def colorize(self, root, fileName, lineNumber, line, matches):
        return [self._pathColor(os.path.join(root, fileName)),
                self._lineNumberColor(str(lineNumber)) + ":",
                self._matchesColor(line.rstrip(), matches)]

    def _lineNumberColor(self, lineNumber):
        return Colors.CYAN + lineNumber + Colors.NO_COLOR

    def _pathColor(self, path):
        return Colors.LIGHT_GRAY + path + Colors.NO_COLOR

    def _matchesColor(self, line, matches):
        result = []
        previous = 0
        spans = getUnionOfSpans(matches)
        for span in spans:
            result.append(line[previous:span[0]])
            result.append(self._matchColor(line[span[0]:span[1]]))
            previous = span[1]
        result.append(line[previous:])

        return "".join(result)

    def _matchColor(self, match):
        return Colors.BROWN + match + Colors.NO_COLOR


class NopColorizer:
    def __init__(self):
        pass

    def colorize(self, root, fileName, lineNumber, line, matches):
        return [os.path.join(root, fileName),
                str(lineNumber) + ":",
                line.rstrip()]


@contextlib.contextmanager
def none():
    yield None

class FileSearcher:
    def __init__(self, inputArgs, matchCallback, printCallback):
        self._matchCallback = matchCallback
        self._maxLineLength = 200
        self._ignoreCase = inputArgs.ignore_case
        self._printCallback = printCallback
        self._replace = 0
        if inputArgs.replace is not None:
            self._replace = 1
        elif inputArgs.query_replace is not None:
            self._replace = 2

    def searchFile(self, root, f):
        filePath = os.path.join(root, f)

        try:
            with tempfile.NamedTemporaryFile(mode="w") if self._replace > 0 else none() as replacedFile:
                lineNumber = 0
                numMatchingLines = 0
                for line in open(filePath, "r"):
                    lineNumber += 1
                    if len(line) > self._maxLineLength:
                        continue
                    if self._ignoreCase:
                        lineToMatch = line.lower()
                    else:
                        lineToMatch = line

                    (matches, replacedString) = self._matchCallback(lineToMatch)
                    if matches is not None:
                        self._printCallback(line, lineNumber, matches, root, f)
                        numMatchingLines += 1

                    if replacedString is not None:
                        if self._replace == 2 and matches is not None:
                            question = "Replace? (y/n)"
                            answer = input(question).lower()
                            while answer not in ["y", "n"]:
                                answer = input(question).lower()
                            if answer == "n":
                                replacedString = line

                        replacedFile.write(replacedString)

                if (self._replace > 0
                    and numMatchingLines > 0):
                    replacedFile.seek(0) # Hacky workaround. Sometimes we were copying an empty file
                                         # I think due to replacedFile getting out of scope.
                                         # But that is unlikely with the 'with' statement above.
                                         # So let's keep the seek and hope it works.
                    shutil.copyfile(replacedFile.name, filePath)

        except IOError:
            pass
        except UnicodeDecodeError:
            print("Unicode decode error for", filePath)

def getArguments():
    argumentParser = argparse.ArgumentParser()
    argumentParser.add_argument("search_strings", nargs = "+", help = "Strings to search for.")
    argumentParser.add_argument("-i", "--ignore-case", action = "store_true", help = "Ignore case.")
    argumentParser.add_argument("-d", "--directory", type = str, default = ".", help = "Directory to search in. Default '.'.")
    argumentParser.add_argument("-e", "--extensions", type = str, default = "c,cc,cpp,h,hh,hpp,py", help = "Extensions to search, comma separated list. Default 'c,cc,cpp,h,hh,hpp,py'.")
    argumentParser.add_argument("-xe", "--exclude-extensions", type = str, default = "", help = "Extensions to exclude from search, comma separated list. Default empty.")
    argumentParser.add_argument("-xd", "--exclude-directories", type = str, default = "", help = "Directories to exclude from search, comma separated list. Default empty.")
    argumentParser.add_argument("-r", "--replace", type = str, default = None, help = "Replace matching strings with provided string. Only works with one search string.")
    argumentParser.add_argument("--query-replace", type = str, default = None, help = "Query-replace matching strings with provided string. Only works with one search string.")
    return argumentParser.parse_args()

def verifyArguments(arguments):
    if (((arguments.replace is not None) or
         (arguments.query_replace is not None))
        and len(arguments.search_strings) > 1):
        print("Must only have one search string when replacing.")
        sys.exit(1)

if __name__ != "__main__":
    print("Don't import s.py.")
    sys.exit(1)
else:
    inputArgs = getArguments()
    verifyArguments(inputArgs)

    matcher = Matcher(inputArgs)
    if os.fstat(0) == os.fstat(1): # https://stackoverflow.com/a/1512526
        colorizer = Colorizer()
    else:
        colorizer = NopColorizer()
    printer = Printer(colorizer)
    fileChecker = FileSearcher(inputArgs, matcher.matchString, printer.print)
    walker = Walker(inputArgs, fileChecker.searchFile)
    walker.walk()
