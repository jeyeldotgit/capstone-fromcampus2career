export interface CourseSeedRow {
  id: string;
  code: string;
  title: string;
  units: number | null;
  description: string;
  is_active: boolean;
}

function course(
  id: string,
  code: string,
  title: string,
  description: string,
): CourseSeedRow {
  return {
    id,
    code,
    title,
    units: null,
    description,
    is_active: true,
  };
}

export const COURSES: CourseSeedRow[] = [
  course(
    "10000000-0000-0000-0000-000000000001",
    "IT101",
    "Introduction to Computing",
    "Foundational computing exposure with light SQL, Linux, and networking context.",
  ),
  course(
    "10000000-0000-0000-0000-000000000002",
    "IT102",
    "Computer Programming 1",
    "Introductory programming with C, Python, Java, and light OOP exposure.",
  ),
  course(
    "10000000-0000-0000-0000-000000000003",
    "IT103",
    "Discrete Mathematics",
    "Academic discrete mathematics mapped to industry proxy skills for set, relational, and algorithmic reasoning.",
  ),
  course(
    "10000000-0000-0000-0000-000000000004",
    "GE101",
    "Understanding the Self",
    "General education course with no technical skill mappings.",
  ),
  course(
    "10000000-0000-0000-0000-000000000005",
    "GE102",
    "Mathematics in the Modern World",
    "Quantitative reasoning mapped to light statistical and data analysis exposure.",
  ),
  course(
    "10000000-0000-0000-0000-000000000006",
    "IT201",
    "Data Structures and Algorithms",
    "Data structures and algorithms mapped to implementation languages and problem-solving contexts.",
  ),
  course(
    "10000000-0000-0000-0000-000000000007",
    "IT202",
    "Object-Oriented Programming",
    "Direct OOP coverage with Java, Python, and C++ implementation practice.",
  ),
  course(
    "10000000-0000-0000-0000-000000000008",
    "IT203",
    "Database Management Systems",
    "SQL, database design, relational engines, indexing, and ORM usage.",
  ),
  course(
    "10000000-0000-0000-0000-000000000009",
    "IT204",
    "Web Development",
    "Frontend web foundations with JavaScript, styling frameworks, backend tier, and REST API exposure.",
  ),
  course(
    "10000000-0000-0000-0000-000000000010",
    "IT205",
    "Human Computer Interaction",
    "UI/UX-oriented course mapped to accessibility, responsive design, and light Tailwind CSS exposure.",
  ),
  course(
    "10000000-0000-0000-0000-000000000011",
    "IT301",
    "Information Assurance and Security",
    "Security course covering cryptography, network security, web application security, IAM, and secure coding.",
  ),
  course(
    "10000000-0000-0000-0000-000000000012",
    "IT302",
    "Networking 1",
    "Networking fundamentals, protocols, administration, troubleshooting, and Linux-based tooling.",
  ),
  course(
    "10000000-0000-0000-0000-000000000013",
    "IT303",
    "Systems Analysis and Design",
    "Systems analysis and design mapped to REST API, data modeling, and SQL proxy skills.",
  ),
  course(
    "10000000-0000-0000-0000-000000000014",
    "IT304",
    "Mobile Application Development",
    "Mobile development course covering Android, Kotlin, React Native, Flutter, OOP, and Java.",
  ),
  course(
    "10000000-0000-0000-0000-000000000015",
    "IT305",
    "Software Engineering",
    "Software engineering course mapped to CI/CD, GitHub Actions, Docker, and secure web delivery practices.",
  ),
  course(
    "10000000-0000-0000-0000-000000000016",
    "IT401",
    "Capstone Project 1",
    "Capstone planning and design with full-stack web, database, REST API, and version-control exposure.",
  ),
  course(
    "10000000-0000-0000-0000-000000000017",
    "IT402",
    "Capstone Project 2",
    "Capstone implementation and deployment with Docker, cloud, CI/CD, APIs, SQL, and security exposure.",
  ),
  course(
    "10000000-0000-0000-0000-000000000018",
    "IT403",
    "Internship / OJT",
    "Broad professional exposure with stack-dependent skill development represented at conservative weights.",
  ),
  course(
    "10000000-0000-0000-0000-000000000019",
    "IT404",
    "IT Elective (Cloud / AI focus)",
    "Elective coverage for cloud fundamentals, AWS, Docker, Python, machine learning, and Linux.",
  ),
  course(
    "20000000-0000-0000-0000-000000000001",
    "CS101",
    "Introduction to Computing (BSCS)",
    "BSCS introductory computing course with Python, Linux, and networking exposure.",
  ),
  course(
    "20000000-0000-0000-0000-000000000002",
    "CS102",
    "Programming Fundamentals",
    "BSCS programming fundamentals using C and Python with light OOP exposure.",
  ),
  course(
    "20000000-0000-0000-0000-000000000003",
    "CS103",
    "Discrete Structures",
    "Academic discrete structures mapped to SQL and Python as industry-relevant proxy skills.",
  ),
  course(
    "20000000-0000-0000-0000-000000000004",
    "MATH101",
    "Calculus 1",
    "Calculus mapped to statistical analysis and numerical-computing proxy skills.",
  ),
  course(
    "20000000-0000-0000-0000-000000000005",
    "CS201",
    "Data Structures",
    "BSCS data structures course emphasizing C++, Python, and Java implementation.",
  ),
  course(
    "20000000-0000-0000-0000-000000000006",
    "CS202",
    "Algorithms",
    "Algorithm design mapped to Python, C++, and statistical reasoning proxy skills.",
  ),
  course(
    "20000000-0000-0000-0000-000000000007",
    "CS203",
    "Computer Organization",
    "Low-level systems course mapped to Linux administration, shell scripting, and C.",
  ),
  course(
    "20000000-0000-0000-0000-000000000008",
    "CS204",
    "Operating Systems",
    "Operating systems course mapped to Linux administration, shell scripting, Docker, and network security.",
  ),
  course(
    "20000000-0000-0000-0000-000000000009",
    "CS301",
    "Theory of Computation",
    "Theory course mapped lightly to Python and shell scripting implementation contexts.",
  ),
  course(
    "20000000-0000-0000-0000-000000000010",
    "CS302",
    "Artificial Intelligence",
    "AI course covering machine learning, Python, Scikit-learn, Pandas, NumPy, analysis, and visualization.",
  ),
  course(
    "20000000-0000-0000-0000-000000000011",
    "CS303",
    "Software Engineering",
    "BSCS software engineering course with stronger CI/CD, GitHub Actions, Docker, and secure coding depth.",
  ),
  course(
    "20000000-0000-0000-0000-000000000012",
    "CS304",
    "Programming Languages",
    "Programming languages course mapped to OOP, Python, Java, and shell scripting exposure.",
  ),
  course(
    "20000000-0000-0000-0000-000000000013",
    "CS401",
    "Thesis 1",
    "Research and system design phase with REST API, SQL, database design, Python, automation, and analysis.",
  ),
  course(
    "20000000-0000-0000-0000-000000000014",
    "CS402",
    "Thesis 2",
    "Thesis implementation and defense with Docker, cloud deployment, visualization, CI/CD, SQL, and security.",
  ),
  course(
    "20000000-0000-0000-0000-000000000015",
    "CS403",
    "Internship / OJT (BSCS)",
    "Broad BSCS professional exposure with backend, data, DevOps, API, SQL, and Linux contexts.",
  ),
  course(
    "20000000-0000-0000-0000-000000000016",
    "CS404",
    "CS Elective (ML / Data Science focus)",
    "Machine learning and data science elective covering Python, ML, deep learning, NLP, and data tooling.",
  ),
];
