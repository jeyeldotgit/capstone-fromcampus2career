# P1-S05 Courses Seed Notes

## Baseline Counts

- `courses`: 35 rows.
- `course_skills`: 155 rows.
- Program coverage: 19 BSIT-oriented courses and 16 BSCS-oriented courses.

## GE101 Exception

`GE101` (`Understanding the Self`) is intentionally inserted as a course but has no `course_skills` rows. It is a general education course with no technical skill counterpart in the labor-market skill taxonomy, so creating a weak proxy mapping would add noise to student skill profiles.

## Mapping Rationale

The taxonomy is a labor-market technology taxonomy, not an academic concept taxonomy. Courses that directly teach market skills map to their closest active skill rows at higher depth weights, such as `IT203` to SQL and Database Design or `CS302` to Machine Learning.

Academic concepts without direct DB counterparts are mapped conservatively to active proxy skills at `0.25` where useful. Examples include Discrete Mathematics and Discrete Structures mapping to SQL plus Python for relational reasoning and algorithmic thinking, Calculus mapping to Statistical Analysis plus NumPy, and Theory of Computation mapping lightly to Python plus Shell Scripting as implementation contexts.

## Inactive Skill Exclusions

The seed excludes all inactive skills from course mappings:

- `SK010` Swift
- `SK012` Rust
- `SK014` MATLAB
- `SK036` iOS Development
- `SK092` Malware Analysis
- `SK099` VoIP and Unified Communications
