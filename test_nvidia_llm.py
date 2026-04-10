from app.nvidia_llm_recommender import NvidiaLLMRecommender

recommender = NvidiaLLMRecommender("/Users/adrianpothanah/Plant_Disease_Management_System/Plant-Disease-Management-System/data/final_recommendation_knowledge_base.json")

result = recommender.generate("Tomato_Early_Blight", "Moderate")

print("\nRESULT:\n")
print(result)