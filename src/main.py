# src/main.py

import sys
from parser import KrpsimParser

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <config_file_path>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    
    # appel du parseur et recuperation des variable stockee dedans
    parser = KrpsimParser()


    


            