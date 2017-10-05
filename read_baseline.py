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

def compare_parameters(test, baseline):
    ret = 0
    for key in ["bw", "std_dev_bw", "avg_iops", "std_dev_iops", "avg_lat",
                "std_dev_lat"]:
        if test[key] < baseline[key]/10:
            ret = 1
            logger.info('%s test failed', key)
        else:
            logger.info('%s test passed', key)
    return ret 

def compare_with_baseline(btype, fpath, baseline):
    ret = 0
    test_result = {}
    with open(fpath) as fd:
        result = json.load(fd)
    if btype == "radosbench":
        test_result["bw"] = float(result["Bandwidth (MB/sec)"])
        test_result["std_dev_bw"] = float(result["Stddev Bandwidth"])
        test_result["avg_iops"] = float(result["Average IOPS"])
        test_result["std_dev_iops"] = float(result["Stddev IOPS"])
        test_result["avg_lat"] = float(result["Average Latency(s)"])
        test_result["std_dev_lat"] = float(result["Stddev Latency(s)"])
    logger.info('Baseline values: %s', baseline)
    logger.info('Test Values: %s', test_result)
    if btype == "librbdfio":
        pass

    ret = compare_parameters(test_result, baseline)
    return ret

def main(argv):
    setup_loggers()
    config = sys.argv[1]
    results = sys.argv[2]
    with open(config) as fd:
        parameters = yaml.load(fd)
    iterations = parameters["cluster"]["iterations"]
    btype = parameters["benchmarks"].keys()[0]
    logger.info('Starting Peformance Tests for %s', btype)
    ret_vals = {}
    for iteration in range(iterations):
        logger.info('Iteration: %d', iteration)
        cbt_dir_path = os.path.join(results, '%08d' % iteration)
        result_files = get_result_files(cbt_dir_path)
        failed_test = []
        for fname in result_files:
            ret = 0
            logger.info('Running performance test for: %s', fname)
            fpath = os.path.join(cbt_dir_path, fname)
            ret = compare_with_baseline(btype, fpath, parameters["baseline"])
            if ret != 0:
                failed_test.append(fname)
        ret_vals[iteration] = failed_test
        if failed_test:
            logger.info('Failed tests in iteration %d: %s', iteration, failed_test)
        else:
            logger.info('All performance tests passed for iteration: %d', iteration)    
    
    # Summary of Performance Tests
    logger.info('Summary of Performance Tests')
    failed = 0
    for iteration in range(iterations):
        if ret_vals[iteration]:
            logger.info('Failed performance tests in iteration %d: %s', iteration, ret_vals[iteration])
            failed = 1
    if failed == 1:
        raise Exception('Performance test failed')
    logger.info('All Performance Tests Succeeded!')

if __name__ == '__main__':
    exit(main(sys.argv))
