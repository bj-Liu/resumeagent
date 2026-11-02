"""Validate independent human review plumbing; synthetic ratings are unit fixtures only."""
import json
from pathlib import Path
import tempfile
import unittest
from evals.visual import CRITERIA, export_review, score_review


class VisualTests(unittest.TestCase):
    def test_export_requires_real_render_flag_and_matching_input_hashes(self):
        from PIL import Image
        from evals.support import load_cases
        from evals.benchmark import input_digest
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            file=root/'report.json';file.write_text(json.dumps({'browser':'mock'}))
            with self.assertRaises(ValueError):
                export_review(file,root/'review')
            # Tiny image and ratings below are unit fixtures, not measured visual quality evidence.
            image=root/'fixture.png';Image.new('RGB',(8,8)).save(image)
            case=load_cases()[1]
            report={'browser':'edge','cases':[case],
                    'methodology':{'paired_input_sha256':{case['case_id']:input_digest(case)}},
                    'primary_runs':[{'run_id':'unit-run','variant':'SECRET_VARIANT','case_id':case['case_id'],'input_sha256':input_digest(case),
                                     'snapshots':[{'page_id':'unit-page','html_name':'index.html','description':'Fixture page','screenshot':str(image)}]}]}
            file.write_text(json.dumps(report))
            manifest=export_review(file,root/'review')
            self.assertEqual(len(manifest['candidates']),1)
            self.assertNotIn('SECRET_VARIANT',json.dumps(manifest))
            self.assertTrue((root/'review/cases.json').exists())
            report['methodology']['paired_input_sha256'][case['case_id']]='wrong'
            file.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                export_review(file,root/'mismatched')

    def test_blank_or_incomplete_ratings_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            manifest={'candidates':[{'candidate_id':'one'}],'source_report_sha256':'digest'}
            labels={'one':{'variant':'baseline'}}
            for name,data in [('manifest',manifest),('labels',labels),('ratings',{'reviewer_id':'fixture-reviewer','ratings':[{'candidate_id':'one',**{c:None for c in CRITERIA}}]})]:
                (root/f'{name}.json').write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                score_review(root/'manifest.json',root/'labels.json',root/'ratings.json')
            # Validate arithmetic with explicit unit-test scores; do not write benchmark scores.
            rating={'reviewer_id':'unit-fixture-not-a-human-review','ratings':[{'candidate_id':'one',**dict(zip(CRITERIA,[2,3,4,5]))}]}
            (root/'ratings.json').write_text(json.dumps(rating))
            result=score_review(root/'manifest.json',root/'labels.json',root/'ratings.json')
            self.assertEqual(result['variants']['baseline']['mean_score'],3.5)


if __name__=='__main__':
    unittest.main()
