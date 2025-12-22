# config.py

# Temperatures to test
TEMPERATURES = [0.2, 0.5, 0.8]

# Context lengths (simulate truncation / small context windows)
CONTEXT_LENGTHS = [512, 1024, 2048]

# Example test input (de-identified, synthetic)
TEST_INPUT = """
The client is a 7-year-old child referred for concerns related to attention,
impulsivity, and academic performance. Parent reports difficulty sustaining
attention during classroom tasks and frequent distractibility at home.

Teacher observations indicate inconsistent task completion and challenges
with following multi-step instructions. Behavioral rating scales completed
by both parents and teachers indicate elevated scores in the areas of
inattention and executive functioning.

Cognitive testing revealed overall average intellectual functioning.
Strengths were noted in verbal comprehension, while working memory and
processing speed scores were comparatively weaker.

No significant emotional or behavioral concerns were reported beyond
attention-related difficulties. The child demonstrates age-appropriate
social engagement and communication skills.
""".strip()
