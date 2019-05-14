# BEGIN_COPYRIGHT
#
# Copyright 2009-2019 CRS4.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy
# of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# END_COPYRIGHT

import unittest
import tempfile
import os
import stat
import shutil
import subprocess as sp

from xml.dom.minidom import getDOMImplementation

DOM_IMPL = getDOMImplementation()

import pydoop.hadoop_utils as hu


class TestHadoopUtils(unittest.TestCase):

    def setUp(self):
        self.hadoop_home = tempfile.mkdtemp(prefix="pydoop_test_")
        self.hadoop_conf = os.path.join(self.hadoop_home, "conf")
        os.mkdir(self.hadoop_conf)
        self.bindir = os.path.join(self.hadoop_home, "bin")
        os.mkdir(self.bindir)
        self.hadoop_exe = os.path.join(self.bindir, "hadoop")
        with open(self.hadoop_exe, "w") as fo:
            fd = fo.fileno()
            os.fchmod(fd, os.fstat(fd).st_mode | stat.S_IXUSR)
            fo.write("#!/bin/bash\necho Hadoop 3.2.0\n")
        self.orig_env = os.environ.copy()
        self.pf = hu.PathFinder()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.orig_env)
        shutil.rmtree(self.hadoop_home)

    def test_get_hadoop_exec(self):
        # hadoop home as argument
        self.assertEqual(
            self.pf.hadoop_exec(hadoop_home=self.hadoop_home), self.hadoop_exe
        )
        # hadoop home from environment
        os.environ["HADOOP_HOME"] = self.hadoop_home
        self.assertEqual(self.pf.hadoop_exec(), self.hadoop_exe)
        # no hadoop home in environment
        del os.environ["HADOOP_HOME"]
        os.environ["PATH"] = self.bindir
        hadoop_exec = self.pf.hadoop_exec()
        cmd = sp.Popen([hadoop_exec, "version"], env=self.orig_env,
                       stdout=sp.PIPE, stderr=sp.PIPE)
        out, _ = cmd.communicate()
        self.assertTrue(
            out.splitlines()[0].strip().lower().startswith(b"hadoop")
        )

    def test_get_hadoop_params(self):
        self.__check_params()
        self.__check_params('', {})
        self.__check_params('<?xml version="1.0"?>', {})
        doc = DOM_IMPL.createDocument(None, "configuration", None)
        self.__check_params(doc.toxml(), {})
        root = doc.documentElement
        prop = root.appendChild(doc.createElement("property"))
        self.__check_params(doc.toxml(), {})
        for s in "name", "value":
            n = prop.appendChild(doc.createElement(s))
            n.appendChild(doc.createTextNode(s.upper()))
        self.__check_params(doc.toxml(), {"NAME": "VALUE"})

    def __check_params(self, xml_content=None, expected=None):
        if expected is None:
            expected = {}
        xml_fn = os.path.join(self.hadoop_conf, "core-site.xml")
        if os.path.exists(xml_fn):
            os.remove(xml_fn)
        if xml_content is not None:
            with open(xml_fn, "w") as fo:
                fo.write(xml_content)
        params = self.pf.hadoop_params(hadoop_conf=self.hadoop_conf)
        self.assertEqual(params, expected)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(TestHadoopUtils('test_get_hadoop_exec'))
    suite.addTest(TestHadoopUtils('test_get_hadoop_params'))
    return suite


if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run((suite()))
