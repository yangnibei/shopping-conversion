"""Offline helper checks; full-data reconciliation checks also run in analysis.py."""
import io
import unittest
from zipfile import ZipFile
import numpy as np
from utils import member_bytes, plain
class HelperTests(unittest.TestCase):
    def test_nested_archive(self):
        inner=io.BytesIO()
        with ZipFile(inner,"w") as z: z.writestr("nested/sample.csv","a,b\n1,2\n")
        outer=io.BytesIO()
        with ZipFile(outer,"w") as z: z.writestr("inner.zip",inner.getvalue())
        self.assertEqual(member_bytes(outer.getvalue(),"sample.csv"),b"a,b\n1,2\n")
    def test_missing_member(self):
        data=io.BytesIO()
        with ZipFile(data,"w") as z: z.writestr("x.txt","x")
        with self.assertRaises(FileNotFoundError): member_bytes(data.getvalue(),"missing.csv")
    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError): plain(float("nan"))
    def test_numpy_json_safe(self):
        self.assertEqual(plain({"n":np.int64(3),"x":np.array([1,2])}),{"n":3,"x":[1,2]})
if __name__=="__main__": unittest.main()

