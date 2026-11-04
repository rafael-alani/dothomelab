import io
import unittest
from test_archive import ArchiveTests
import transcripts


class TranscriptTests(ArchiveTests):
    def test_selection_validation_and_cache(self):
        a = self.archive
        a.put(self.header, io.BytesIO(self.body))
        for ids in ([], ['../secret'], ['f' * 64], [self.digest] * 51):
            with self.assertRaises(ValueError):
                transcripts.request(a, ids)
        self.assertEqual(transcripts.request(a, [self.digest])[0]['status'], 'pending')
        a.db.execute("UPDATE transcripts SET status='ready',result=?", ('{"text":"cached"}',)); a.db.commit()
        self.assertEqual(transcripts.request(a, [self.digest])[0]['result']['text'], 'cached')
        with self.assertRaises(ValueError):
            transcripts.request(a, [self.digest], 'arbitrary-download')

    def test_reject_empty_or_invalid_segments(self):
        valid = {'duration': 2, 'text': 'Hello', 'segments': [{'start': 0, 'end': 1, 'text': 'Hello'}]}
        self.assertEqual(transcripts.validate(valid), valid)
        for invalid in ({**valid, 'segments': []}, {**valid, 'duration': float('nan')},
                        {**valid, 'segments': [{'start': 2, 'end': 1, 'text': 'oops'}]}):
            with self.assertRaises(ValueError):
                transcripts.validate(invalid)


if __name__ == '__main__':
    unittest.main()
