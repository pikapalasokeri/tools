#!/usr/bin/python3

import sys
import matplotlib.pyplot as plt
import argparse
import numpy as np
import os

def sign(x):
    if x < 0.0:
        return -1.0
    else:
        return 1.0

def strIsFloat(candidate):
    try:
        float(candidate)
        return True
    except ValueError:
        return False

def getColumnList(colArg):
    result = []
    rangeCandidates = colArg.split(",")
    for candidate in rangeCandidates:
        if ":" in candidate:
            endpoints = candidate.split(":")
            if len(endpoints) != 2:
                raise Exception("Column range must have exactly two endpoints")
            endpoints = sorted([int(x) for x in endpoints])
            end1 = endpoints[0]
            end2 = endpoints[1]
            if sign(end1) == sign(end2):
                endpoints = [end1, end2]
            else:
                 # need own range function for sign is different case
                raise Exception("Start and end sign in column range must not differ")
                endpoints = [end2, end1]

            result.extend(range(endpoints[0], endpoints[1] + 1))
        else:
            result.append(int(candidate))

    return result

def evalFunction(function, value):
    if function:
        result = eval(function.replace("__X__", str(value)))
        return result
    else:
        return value

def getArgsWithCorrectDashes(args, argParser):
    hackedArgs = args
    nonOptionArgumentsSoFar = 0
    for ix, arg in enumerate(hackedArgs[1:]):
        if not arg.startswith("--"):
            nonOptionArgumentsSoFar += 1
        if nonOptionArgumentsSoFar == 2:
            hackedArgs[ix+1] = arg.replace("-", "&")
            break
    return argParser.parse_args(hackedArgs[1:])

def findDelimiter(line):
    # Space is last since "," might be in ", " in files. " " might also be in
    # header column names.
    candidates = ["\t", ",", " "]
    for candidate in candidates:
        if candidate in line:
            return candidate

    # We reach default if we only have one column for example.
    default = " "
    return default


def getFileName(path):
    return os.path.basename(path)

if __name__ == "__main__":
    argParser = argparse.ArgumentParser()
    argParser.add_argument("file_path", nargs=1, help="Path to file containing data for plotting.")
    argParser.add_argument("columns", nargs=1, help="Columns to parse and plot.")
    argParser.add_argument("--xyy", action="store_true", default=False, help="Plot as xy plot if set. Requires two or more columns. The first column is treated as x-axis, the rest as y-axes.")
    argParser.add_argument("--xyxy", action="store_true", default=False, help="Plot as xy plot if set. Requires a factor of two columns. The columns are alternatingly treated as x-axis and y-axis.")
    argParser.add_argument("--dots", action="store_true", default=False, help="Plot as dots instead of lines.")
    argParser.add_argument("--eval", type=str, default="", metavar="expression", help="Expression which will be evaluated on each data point. Use __X__ as data variable. Numpy can be used as np. Example 'np.asin(__X__)*2'")
    argParser.add_argument("--delimiter", type=str, default=None, metavar="string", help="Delimiter used to separate data fields.")
    args = getArgsWithCorrectDashes(sys.argv, argParser)

    columns = getColumnList(args.columns[0].replace("&", "-"))
    path = args.file_path[0]
    print("Parsing data from '{0}'".format(path))

    function = args.eval
    delimiter = args.delimiter

    data = [[] for _ in range(700)]
    header = None

    with open(path) as f:
        for ix, line in enumerate(f):
            if delimiter is None:
                delimiter = findDelimiter(line)

            tokens = line.strip().split(delimiter)
            tokens = list(filter(None, tokens))
            if not strIsFloat(tokens[0]):
                if header is None and ix == 0:
                    header = tokens
                continue

            for ix, token in enumerate(tokens):
                data[ix].append(evalFunction(function, float(token)))

    if header is None:
        header = {c: str(c) for c in columns}

    plotStyle = ".-"
    if args.dots:
        plotStyle = "."

    print("Plotting")
    data = [x for x in data if x != []]
    if args.xyy:
        fig = plt.figure()
        nCols = len(columns)
        if nCols < 2:
            raise Exception("Must have 2 or more columns with --xyy option.")

        ax = fig.add_subplot(111)
        legend = []
        xData = data[columns[0]]
        for col in columns[1:]:
            yData = data[col]
            ax.plot(xData, yData, plotStyle)
            if header is not None:
                legend.append(header[col])
        if header is not None:
            ax.set_xlabel(header[columns[0]])
            plt.legend(legend)
    elif args.xyxy:
        fig = plt.figure()
        nCols = len(columns)
        if nCols % 2 != 0:
            raise Exception("Must have a factor of 2 columns with --xyxy option.")

        ax = fig.add_subplot(111)
        legend = []
        numPairs = nCols // 2
        for ix in range(numPairs):
            xIx = ix * 2
            yIx = xIx + 1
            xData = data[columns[xIx]]
            yData = data[columns[yIx]]
            ax.plot(xData, yData, plotStyle)
            if header is not None:
                legend.append(f"{header[columns[xIx]]} vs {header[columns[yIx]]}")
        if header is not None:
            plt.legend(legend)
    else:
        for ix in columns:
            plt.plot(data[ix], plotStyle)
        if header is not None:
            legend = [header[col] for col in columns]
            plt.legend(legend)

    plt.title(getFileName(path))
    plt.grid()
    plt.show()
