from pathlib import Path

APP_TITLE = "Universal AI Job Matcher"
APP_LAYOUT = "wide"
MODEL_NAME = "all-MiniLM-L6-v2"

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "app_logs"
DB_PATH = BASE_DIR / "jobfinder.db"
LOG_FILE = LOG_DIR / "job_matcher.log"

ROLE_CATALOG = [
    "Data Engineer", "Senior Data Engineer", "Data Analyst", "Business Data Analyst", "Data Scientist",
    "Machine Learning Engineer", "AI Engineer", "NLP Engineer", "MLOps Engineer", "BI Developer",
    "BI Analyst", "Analytics Engineer", "Software Engineer", "Backend Developer", "Frontend Developer",
    "Full Stack Developer", "Python Developer", "Java Developer", "Node.js Developer", "Mobile Developer",
    "Android Developer", "iOS Developer", "DevOps Engineer", "Site Reliability Engineer", "Cloud Engineer",
    "Cloud Architect", "Platform Engineer", "Cybersecurity Engineer", "Security Analyst", "QA Engineer",
    "Test Automation Engineer", "Product Manager", "Technical Product Manager", "Project Manager",
    "Program Manager", "Scrum Master", "Solutions Architect", "System Administrator", "Database Administrator",
    "Financial Analyst", "Accountant", "HR Specialist", "Talent Acquisition Specialist", "Recruiter",
    "Marketing Specialist", "Digital Marketing Manager", "Sales Manager", "Customer Success Manager",
    "Operations Manager", "Supply Chain Analyst", "Procurement Specialist", "UX Designer", "UI Designer",
    "UX Researcher", "Graphic Designer", "Content Writer", "Business Consultant",
]

SOURCE_OPTIONS = {
    "LinkedIn": "linkedin",
    "Google Jobs": "google",
    "Indeed": "indeed",
}

SKILL_KEYWORDS = [
    "python", "java", "javascript", "typescript", "c#", "c++", "go", "rust", "php", "ruby",
    "sql", "nosql", "postgresql", "mysql", "sql server", "mongodb", "redis", "elasticsearch",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras", "xgboost", "lightgbm",
    "spark", "pyspark", "hadoop", "hive", "airflow", "dbt", "kafka", "flink", "databricks",
    "snowflake", "redshift", "bigquery", "synapse", "data factory", "ssis", "power bi", "tableau",
    "qlik", "looker", "excel", "power query", "dax", "mdx", "aws", "azure", "gcp",
    "ec2", "s3", "lambda", "glue", "cloudwatch", "azure devops", "synapse analytics",
    "docker", "kubernetes", "terraform", "ansible", "jenkins", "gitlab ci", "github actions",
    "ci/cd", "git", "github", "gitlab", "bitbucket", "linux", "bash", "shell scripting",
    "rest", "graphql", "api", "fastapi", "django", "flask", "spring", "spring boot", "node.js",
    "react", "angular", "vue", "next.js", "express", "microservices", "event-driven architecture",
    "nlp", "llm", "rag", "langchain", "prompt engineering", "machine learning", "deep learning",
    "computer vision", "time series", "feature engineering", "mlops", "model monitoring",
    "scrum", "agile", "kanban", "jira", "communication", "problem solving", "leadership",
    "stakeholder management", "english", "french",
]

COUNTRY_FALLBACK = [
    "tunisia", "france", "germany", "italy", "spain", "netherlands", "belgium", "switzerland",
    "united_kingdom", "ireland", "portugal", "morocco", "algeria", "egypt", "canada", "usa",
    "australia", "india", "uae", "saudi_arabia", "qatar", "turkey", "south_africa",
]
