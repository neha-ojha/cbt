#!/usr/bin/python
import argparse
import collections
import logging
import pprint
import os
import sys
import yaml
import json

import settings
import benchmarkfactory
from cluster.ceph import Ceph
from log_support import setup_loggers

logger = logging.getLogger("cbt")

def get_result_files(dir_path):
    fnames = []
    for fname in os.listdir(dir_path):
        if "json_" in fname:
            fnames.append(fname)
    return fnames

def compare_with_baseline(cbt_dir_path, fname, baseline):
    ret = 0
    with open(os.path.join(cbt_dir_path, fname)) as fd:
        result = json.load(fd)
    logger.info("JSON results: %s", result)
    logger.info("Output Bandwidth: %s", result["Bandwidth (MB/sec)"])
    logger.info("Baseline Bandwidth: %s", baseline["bw"])
    if float(result["Bandwidth (MB/sec)"]) < float(baseline["bw"]):
        logger.info("Bandwidth test failed")
        ret = 1
        raise Exception('Performance test failed')
    return ret

def main(argv):
    setup_loggers()
    config = sys.argv[1]
    results = sys.argv[2]
    with open(config) as fd:
        parameters = yaml.load(fd)
    logger.info('Baseline Parameters are: %s', parameters["baseline"])
    logger.info('CBT results directory: %s', results)

    iterations = parameters["cluster"]["iterations"]
    for iteration in range(iterations):
        ret = 0
        cbt_dir_path = os.path.join(results, '%08d' % iteration)
        logger.info('CBT dir path: %s', cbt_dir_path)
        result_files = get_result_files(cbt_dir_path)
        logger.info('Results filenames: %s', result_files)
        ret = 0
        for fname in result_files:
            ret = compare_with_baseline(cbt_dir_path, fname, parameters["baseline"])
            if ret != 0:
                break
    return ret

if __name__ == '__main__':
    exit(main(sys.argv))
