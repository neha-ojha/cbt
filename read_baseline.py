#!/usr/bin/python
import logging
import pprint
import os
import sys
import yaml
import json

from log_support import setup_loggers

logger = logging.getLogger("cbt")

def generate_result_files(dir_path, clients, instances, mode, btype):
    result_files = []
    for fname in os.listdir(dir_path):
        if os.path.isdir(os.path.join(dir_path, fname)):
            for client in clients:
                for i in xrange(instances):
                    if btype == "radosbench":
                        json_out_file = '%s/%s/json_output.%s.%s' % (fname, mode, i, client)
                    else:
                        json_out_file = '%s/json_output.%s.%s' % (fname, i, client)
                    result_files.append(json_out_file)
    if len(result_files) == 0:
        raise Exception('Performance test failed: no result files found')
    return result_files

def compare_parameters(btype, mode, mode1, test, baseline):
    ret = 0
    if btype == "librbdfio":
        params = ["bw", "avg_iops", "std_dev_iops", "avg_lat", "std_dev_lat"]
    else:
        params = ["bw", "std_dev_bw", "avg_iops", "std_dev_iops", "avg_lat",
                  "std_dev_lat"]
    # this is only for the rw case
    if mode1:
        params.extend(["read_bw", "read_avg_iops", "read_std_dev_iops",
                       "read_avg_lat", "read_std_dev_lat"])

    for key in params:
        if test[key] < baseline[key] / 2:
            ret = 1
            logger.info('%s test failed', key)
        else:
            logger.info('%s test passed', key)
    return ret 

def compare_with_baseline(btype, test_mode, fpath, baseline):
    ret = 0
    mode = ""
    mode1 = ""
    test_result = {}
    with open(fpath) as fd:
        result = json.load(fd)
    # default bw MB/sec and lat sec
    if btype == "radosbench":
        test_result["bw"] = float(result["Bandwidth (MB/sec)"])
        test_result["std_dev_bw"] = float(result["Stddev Bandwidth"])
        test_result["avg_iops"] = float(result["Average IOPS"])
        test_result["std_dev_iops"] = float(result["Stddev IOPS"])
        test_result["avg_lat"] = float(result["Average Latency(s)"])
        test_result["std_dev_lat"] = float(result["Stddev Latency(s)"])

    # default bw KiB/s and default ns, we convert it to MB/sec and sec
    if btype == "librbdfio":
        if test_mode[0] in ['read', 'randread']:
            mode = 'read'
        if test_mode[0] in ['write', 'randwrite']:
            mode = 'write'
        if test_mode[0] in ['rw', 'randrw']:
            mode = 'write'
            mode1 = 'read'
        test_result["bw"] = float(result["jobs"][0][mode]["bw"]) * 0.001024
        test_result["avg_iops"] = float(result["jobs"][0][mode]["iops_mean"])
        test_result["std_dev_iops"] = float(result["jobs"][0][mode]["iops_stddev"])
        test_result["avg_lat"] = float(result["jobs"][0][mode]["lat_ns"]["mean"]) / (10**9)
        test_result["std_dev_lat"] = float(result["jobs"][0][mode]["lat_ns"]["stddev"]) / (10**9)

        if mode1:
            test_result["read_bw"] = float(result["jobs"][0][mode1]["bw"]) * 0.001024
            test_result["read_avg_iops"] = float(result["jobs"][0][mode1]["iops_mean"])
            test_result["read_std_dev_iops"] = float(result["jobs"][0][mode1]["iops_stddev"])
            test_result["read_avg_lat"] = float(result["jobs"][0][mode1]["lat_ns"]["mean"]) / (10**9)
            test_result["read_std_dev_lat"] = float(result["jobs"][0][mode1]["lat_ns"]["stddev"]) / (10**9)


    logger.info("Baseline values:\n    %s",
                 pprint.pformat(baseline).replace("\n", "\n    "))

    logger.info("Test values:\n    %s",
                 pprint.pformat(test_result).replace("\n", "\n    "))

    ret = compare_parameters(btype, mode, mode1, test_result, baseline)
    return ret

def main(argv):
    setup_loggers()
    config = sys.argv[1]
    results = sys.argv[2]
    with open(config) as fd:
        parameters = yaml.load(fd)
    btype = parameters["benchmarks"].keys()[0]
    logger.info('Starting Peformance Tests for %s', btype)
    if not parameters["baseline"]:
        raise Exception('Performance test failed: no baseline parameters provided')

    iterations = parameters["cluster"]["iterations"]
    clients = parameters["cluster"]["clients"]

    if btype == "radosbench":
        instances = parameters["benchmarks"][btype]["concurrent_procs"]
        if parameters["benchmarks"][btype]["write_only"]:
            mode = 'write'
        else:
            if "readmode" in parameters["benchmarks"][btype].keys():
                mode = parameters["benchmarks"][btype]["readmode"]
            else:
                mode = 'seq'
    elif btype == "librbdfio":
        instances = parameters["benchmarks"][btype]["volumes_per_client"][0]
        mode = parameters["benchmarks"][btype]["mode"]

    logger.info('Test Mode: %s', mode)
    ret_vals = {}
    for iteration in range(iterations):
        logger.info('Iteration: %d', iteration)
        cbt_dir_path = os.path.join(results, 'results', '%08d' % iteration)
        result_files =  generate_result_files(cbt_dir_path, clients, instances, mode, btype)
        failed_test = []
        for fname in result_files:
            ret = 0
            logger.info('Running performance test on: %s', fname)
            fpath = os.path.join(cbt_dir_path, fname)
            ret = compare_with_baseline(btype, mode, fpath, parameters["baseline"])
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
