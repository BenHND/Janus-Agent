#!/usr/bin/env python3
"""
Example: Voice Fingerprinting (Speaker Verification)
TICKET-STT-002: Demonstrates speaker verification functionality

This example shows how to:
1. Check if speaker verification is enabled
2. Enroll a user with voice samples
3. Verify speaker identity from audio

Note: This is a demonstration script. Actual usage requires resemblyzer to be installed
and proper audio recording setup.
"""

import os
import sys
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from janus.io.stt.speaker_verifier import SpeakerVerifier
from janus.io.stt.voice_enrollment import VoiceEnrollmentManager


def demo_speaker_verification():
    """Demonstrate speaker verification functionality"""
    print("\n" + "="*60)
    print("Voice Fingerprinting Demo (TICKET-STT-002)")
    print("="*60)
    
    # Initialize verifier
    print("\n1. Initializing Speaker Verifier...")
    verifier = SpeakerVerifier(
        embedding_path="demo_user_voice.npy",
        similarity_threshold=0.75,
        sample_rate=16000
    )
    
    if not verifier.is_available():
        print("❌ Speaker verification not available (resemblyzer not installed)")
        print("   Install with: pip install resemblyzer")
        return
    
    print("✓ Speaker verifier initialized")
    print(f"  Threshold: {verifier.similarity_threshold}")
    print(f"  Sample rate: {verifier.sample_rate}Hz")
    
    # Create demo embeddings (in real usage, these come from actual audio)
    print("\n2. Creating Demo Voice Embeddings...")
    print("   (In production, these would be extracted from real audio)")
    
    # Simulate user voice embedding (normalized random vector)
    user_voice = np.random.randn(256).astype(np.float32)
    user_voice = user_voice / np.linalg.norm(user_voice)
    
    # Simulate similar voice (small perturbation of user voice)
    similar_voice = user_voice + np.random.randn(256).astype(np.float32) * 0.1
    similar_voice = similar_voice / np.linalg.norm(similar_voice)
    
    # Simulate different voice (orthogonal vector)
    different_voice = np.random.randn(256).astype(np.float32)
    different_voice = different_voice / np.linalg.norm(different_voice)
    # Make it orthogonal to user_voice
    different_voice = different_voice - (np.dot(different_voice, user_voice) * user_voice)
    different_voice = different_voice / np.linalg.norm(different_voice)
    
    # Save user embedding
    verifier.save_user_embedding(user_voice, "demo_user_voice.npy")
    print("✓ User voice embedding saved")
    
    # Test verification with similar voice
    print("\n3. Testing Speaker Verification...")
    print("\nTest 1: Verifying AUTHORIZED user voice (similar to enrolled voice)")
    similarity1 = verifier._cosine_similarity(user_voice, similar_voice)
    is_verified1 = similarity1 >= verifier.similarity_threshold
    print(f"  Cosine similarity: {similarity1:.3f}")
    print(f"  Threshold: {verifier.similarity_threshold}")
    print(f"  Result: {'✓ VERIFIED' if is_verified1 else '✗ REJECTED'}")
    
    # Test verification with different voice
    print("\nTest 2: Verifying UNAUTHORIZED user voice (different from enrolled voice)")
    similarity2 = verifier._cosine_similarity(user_voice, different_voice)
    is_verified2 = similarity2 >= verifier.similarity_threshold
    print(f"  Cosine similarity: {similarity2:.3f}")
    print(f"  Threshold: {verifier.similarity_threshold}")
    print(f"  Result: {'✓ VERIFIED' if is_verified2 else '✗ REJECTED'}")
    
    # Test enrollment with multiple samples
    print("\n4. Testing Enrollment Process...")
    print("   Simulating enrollment with 3 voice samples")
    
    # Create 3 similar voice samples (small variations)
    samples = []
    for i in range(3):
        sample = user_voice + np.random.randn(256).astype(np.float32) * 0.05
        sample = sample / np.linalg.norm(sample)
        samples.append(sample)
        print(f"  Sample {i+1}: similarity to user voice = {verifier._cosine_similarity(user_voice, sample):.3f}")
    
    # Create average embedding
    avg_embedding = np.mean(samples, axis=0)
    print(f"\n  Average embedding similarity to user voice: {verifier._cosine_similarity(user_voice, avg_embedding):.3f}")
    print("  ✓ Enrollment would succeed with these samples")
    
    # Cleanup
    print("\n5. Cleanup...")
    if os.path.exists("demo_user_voice.npy"):
        os.remove("demo_user_voice.npy")
        print("  ✓ Demo files removed")
    
    print("\n" + "="*60)
    print("Demo completed successfully!")
    print("="*60)
    print("\nKey Takeaways:")
    print("  • Cosine similarity ranges from -1.0 (opposite) to 1.0 (identical)")
    print("  • Threshold of 0.75 provides good security/usability balance")
    print("  • Authorized voices (similar to enrolled) have high similarity (>0.75)")
    print("  • Unauthorized voices (different) have low similarity (<0.75)")
    print("  • Enrollment with 3+ samples creates robust voice profile")
    print()


def demo_enrollment_prompts():
    """Show enrollment prompts that would be used"""
    print("\n" + "="*60)
    print("Voice Enrollment Prompts")
    print("="*60)
    print("\nDuring enrollment, users are asked to read these phrases:")
    
    from janus.io.stt.voice_enrollment import ENROLLMENT_PROMPTS
    for i, prompt in enumerate(ENROLLMENT_PROMPTS, 1):
        print(f"\n{i}. {prompt}")
    
    print("\nThese prompts are designed to:")
    print("  • Capture natural speech patterns")
    print("  • Include common command vocabulary")
    print("  • Provide sufficient audio duration")
    print()


if __name__ == "__main__":
    demo_speaker_verification()
    demo_enrollment_prompts()
