#!/usr/bin/env python
# coding: utf-8


import argparse
import sys
import os
import glob
from tqdm import tqdm

# custom libraries
import ET_Driver as driver

def run(inpath='',
        outpath=''):

    files = glob.glob(inpath+'*')

    ndvi_opt = [False, True]
    rain_opt = [False, True]
    calc_ET_region_opt = [False, True]

    for file in tqdm(files):
      for nopt in tqdm(ndvi_opt, leave=False):
        for ropt in tqdm(rain_opt, leave=False):
          for copt in tqdm(calc_ET_region_opt, leave=False):
              filename = file.split('/')[-1]
              driver.run(datafile=filename,
                          inpath=inpath,
                          outpath=outpath,
                          nofilterndvi=nopt,
                          nofilterrain=ropt,
                          calcETregion=copt)

def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument('--inpath', required=False, default='../../raw_data/', help='Path for input files')
    parser.add_argument('--outpath', required=False, default='../../runs/', help='Path for output files')
    return parser.parse_args()

if __name__ == "__main__":
    opt = parse_opt()
    run(**vars(opt))