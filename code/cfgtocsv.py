import numpy as np
import csv
import configparser



def main():
    configFilePath = "config/config.cfg"
    config = configparser.RawConfigParser()
    config.read(configFilePath)
    sources = []
    for key in config['sources']:
        sourceCoordinates = config.get('sources', key).replace(" ", "").split(",")
        sourceName = key
        raText = str(sourceCoordinates[0])
        decText = str(sourceCoordinates[1])
        source = [sourceName, raText, decText]
        sources.append(source)

    with open('config/config.csv', 'w') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(['Source', 'Ra', 'Dec'])
        for source in sources:
            spamwriter.writerow([source[0], source[1], source[2]])

if __name__=="__main__":
    main()
