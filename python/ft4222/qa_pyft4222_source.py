#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2024 Patrik Kluba <kpajko79@gmail.com>.
#
# SPDX-License-Identifier: GPL-3.0-or-later
#

import unittest
from unittest.mock import patch
from parameterized import parameterized
from gnuradio import gr, gr_unittest

import sys
import io
import numpy as np
from time import sleep
from math import floor

from koda import Err, Ok
from pyft4222.stream import InterfaceType

# from gnuradio import blocks
from gnuradio.ft4222 import pyft4222_source

class gpio_handle:
    def __init__(self):
        global gpio_handle_instance
        gpio_handle_instance = self

    def set_suspend_out(self, arg1):
        pass

    def set_wakeup_interrupt(self, arg1):
        pass

    def write(self, arg1, arg2):
        pass

    def close(self):
        pass

class spi_handle:
    def __init__(self):
        global spi_handle_instance
        spi_handle_instance = self

        self.avail = 0
        self.data = []

    def set_mode(self, arg1, arg2):
        pass

    def reset_transaction(self, arg1):
        pass

    def close(self):
        pass

    def get_rx_status(self):
        return self.avail

    def read(self, amount):
        if amount == 0:
            return 0

        if amount > self.avail:
            sys.exit(1)

        self.avail = self.avail - amount

        return bytes(self.data[:amount])

    def set_data_for_read(self, new_data):
        self.data = new_data
        self.avail = len(new_data)

class gpio_dev_handle:
    def __init__(self):
        self.tag = InterfaceType.GPIO

    def init_gpio(self, gpio_dirs):
        return gpio_handle()

    def close(self):
        pass

class spi_dev_handle:
    def __init__(self):
        self.tag = InterfaceType.DATA_STREAM

    def init_raw_spi_slave(self):
        return spi_handle()

    def close(self):
        pass

def choose_device_by_idx(*args, **kwargs):
    if args[0] == 1:
        return Ok(gpio_dev_handle())
    elif args[0] == 0:
        return Ok(spi_dev_handle())
    sys.exit(1)

class qa_pyft4222_source(gr_unittest.TestCase):

    def setUp(self):
        self.get_device_info_list_patcher = patch('pyft4222.get_device_info_list')
        self.get_device_info_list = self.get_device_info_list_patcher.start()
        self.get_device_info_list.return_value = [ "mock A", "mock B" ]

        self.open_by_idx_patcher = patch('pyft4222.open_by_idx')
        self.open_by_idx = self.open_by_idx_patcher.start()
        self.open_by_idx.side_effect = choose_device_by_idx

        suppress_text = io.StringIO()
        sys.stdout = suppress_text 

    def tearDown(self):
        sys.stdout = sys.__stdout__
        self.open_by_idx_patcher.stop()
        self.get_device_info_list_patcher.stop()

    @parameterized.expand([
        ( 'short',   1, np.int16     ),
        ( 'short',   2, np.int16     ),
        ( 'float',   1, np.float32   ),
        ( 'complex', 1, np.complex64 ),
    ])
    def test_counts(self, source_type, vec_len, dtype):
        instance = pyft4222_source(0, source_type, vec_len)

        unit_len = 2 if source_type == 'complex' else vec_len

        for count in range(32):
            # print("Testing ({}, {}) with a count of {}...".format(source_type, vec_len, count))

            results = count // (2 * unit_len)
            if results == 0:
                output_items = [[]]
            elif vec_len == 1:
                output_items = [ np.zeros(results, dtype=dtype) ]
            else:
                output_items = [ np.zeros((results, vec_len), dtype=dtype) ]

            spi_handle_instance.set_data_for_read(np.full(count, 65, dtype=np.byte))
            instance.start()
            sleep(0.1)
            instance.stop()

            result = instance.work([], output_items)
            self.assertEqual(result, count // (2 * unit_len))
            self.assertEqual(result, len(output_items[0]))

    def test_short_1unsigned(self):
        instance = pyft4222_source(0, 'short', 1)
        output_items = [ np.zeros((1, 1), dtype=np.int16) ]

        # 0x12 0x34 -> 0x1234 = 4660
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 1)
        self.assertEqual(len(output_items[0]), 1)
        self.assertEqual(output_items[0][0], 4660)

    def test_short_2unsigned(self):
        instance = pyft4222_source(0, 'short', 1)
        output_items = [ np.zeros(2, dtype=np.int16) ]

        # 0x12 0x34 0x56 0x78 -> 0x1234 0x5678 = 4660 22136
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34, 0x56, 0x78 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 2)
        self.assertEqual(len(output_items[0]), 2)
        self.assertEqual(output_items[0][0], 4660)
        self.assertEqual(output_items[0][1], 22136)

    def test_short_1signed(self):
        instance = pyft4222_source(0, 'short', 1)
        output_items = [ np.zeros((1, 1), dtype=np.int16) ]

        # 0x87 0x12 -> 0x8712 = -30958
        spi_handle_instance.set_data_for_read(np.array([ 0x87, 0x12 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 1)
        self.assertEqual(len(output_items[0]), 1)
        self.assertEqual(output_items[0][0], -30958)

    def test_short_2signed(self):
        instance = pyft4222_source(0, 'short', 1)
        output_items = [ np.zeros(2, dtype=np.int16) ]

        # 0x87 0x12 0x97 0x34 -> 0x8712 0x9734 = -30958 -26828
        spi_handle_instance.set_data_for_read(np.array([ 0x87, 0x12, 0x97, 0x34 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 2)
        self.assertEqual(len(output_items[0]), 2)
        self.assertEqual(output_items[0][0], -30958)
        self.assertEqual(output_items[0][1], -26828)

    def test_float_1unsigned(self):
        instance = pyft4222_source(0, 'float', 1)
        output_items = [ np.zeros((1, 1), dtype=np.float32) ]

        # 0x12 0x34 -> 0x1234 = 4660 -> 0.1422119140625
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 1)
        self.assertEqual(len(output_items[0]), 1)
        self.assertEqual(output_items[0][0], 0.1422119140625)

    def test_float_2unsigned(self):
        instance = pyft4222_source(0, 'float', 1)
        output_items = [ np.zeros(2, dtype=np.float32) ]

        # 0x12 0x34 0x56 0x78 -> 0x1234 0x5678 = 4660 22136 -> 0.1422119140625 0.675537109375
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34, 0x56, 0x78 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 2)
        self.assertEqual(len(output_items[0]), 2)
        self.assertEqual(output_items[0][0], 0.1422119140625)
        self.assertEqual(output_items[0][1], 0.675537109375)

    def test_float_1signed(self):
        instance = pyft4222_source(0, 'float', 1)
        output_items = [ np.zeros((1, 1), dtype=np.float32) ]

        # 0x87 0x12 -> 0x8712 = -30958 -> -0.94476318359375
        spi_handle_instance.set_data_for_read(np.array([ 0x87, 0x12 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 1)
        self.assertEqual(len(output_items[0]), 1)
        self.assertEqual(output_items[0][0], -0.94476318359375)

    def test_float_2signed(self):
        instance = pyft4222_source(0, 'float', 1)
        output_items = [ np.zeros(2, dtype=np.float32) ]

        # 0x87 0x12 0x97 0x34 -> 0x8712 0x9734 = -30958 -26828 -> -0.94476318359375 -0.8187255859375
        spi_handle_instance.set_data_for_read(np.array([ 0x87, 0x12, 0x97, 0x34 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 2)
        self.assertEqual(len(output_items[0]), 2)
        self.assertEqual(output_items[0][0], -0.94476318359375)
        self.assertEqual(output_items[0][1], -0.8187255859375)

    def test_complex_1(self):
        instance = pyft4222_source(0, 'complex', 1)
        output_items = [ np.zeros((1, 1), dtype=np.complex64) ]

        # 0x12 0x34 0x56 0x78 -> 0x1234 0x5678 = 4660 22136 -> 0.1422119140625+0.675537109375i
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34, 0x56, 0x78 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 1)
        self.assertEqual(len(output_items[0]), 1)
        self.assertEqual(output_items[0][0], 0.1422119140625+0.675537109375j)

    def test_complex_2(self):
        instance = pyft4222_source(0, 'complex', 1)
        output_items = [ np.zeros(2, dtype=np.complex64) ]

        # 0x12 0x34 0x56 0x78 0x87 0x12 0x97 0x34 -> 0x1234 0x5678 0x8712 0x9734 = 4660 22136 -30958 -26828 -> 0.1422119140625+0.675537109375j -0.94476318359375-0.8187255859375j
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34, 0x56, 0x78, 0x87, 0x12, 0x97, 0x34 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 2)
        self.assertEqual(len(output_items[0]), 2)
        self.assertEqual(output_items[0][0], 0.1422119140625+0.675537109375j)
        self.assertEqual(output_items[0][1], -0.94476318359375-0.8187255859375j)

    def test_sc16_1(self):
        instance = pyft4222_source(0, 'short', 2)
        output_items = [ np.zeros((1, 2), dtype=np.int16) ]

        # 0x12 0x34 0x56 0x78 -> 0x1234 0x5678 = 4660 22136
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34, 0x56, 0x78 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 1)
        self.assertEqual(len(output_items[0]), 1)
        self.assertEqual((output_items[0][0] == [ 4660, 22136 ]).all(), True)

    def test_sc16_2(self):
        instance = pyft4222_source(0, 'short', 2)
        output_items = [ np.zeros((2, 2), dtype=np.int16) ]

        # 0x12 0x34 0x56 0x78 0x87 0x12 0x97 0x34 -> 0x1234 0x5678 0x8712 0x9734 = 4660 22136 -30958 -26828
        spi_handle_instance.set_data_for_read(np.array([ 0x12, 0x34, 0x56, 0x78, 0x87, 0x12, 0x97, 0x34 ], dtype=np.byte))
        instance.start()
        sleep(0.1)
        instance.stop()

        result = instance.work([], output_items)
        self.assertEqual(result, 2)
        self.assertEqual(len(output_items[0]), 2)
        self.assertEqual((output_items[0][0] == [ 4660, 22136 ]).all(), True)
        self.assertEqual((output_items[0][1] == [ -30958, -26828 ]).all(), True)

if __name__ == '__main__':
    gr_unittest.run(qa_pyft4222_source)
