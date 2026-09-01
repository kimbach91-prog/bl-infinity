import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';
import type { Participant, Seat } from './types.js';

const ADAPTER_VERSION = 'bl-bridge-runtime/0.1.0';

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function optional(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value || undefined;
}

export function buildParticipants(): Participant[] {
  const participants: Participant[] = [];

  const openAIKey = optional('OPENAI_API_KEY');
  const openAIModel = optional('OPENAI_MODEL');
  if (openAIKey && openAIModel) {
    const client = new OpenAI({ apiKey: openAIKey });
    participants.push({
      seat: 'GPT',
      provider: 'openai',
      model: openAIModel,
      async respond(input: string): Promise<string> {
        const response = await client.responses.create({
          model: openAIModel,
          input
        });
        return response.output_text?.trim() || '[GPT returned no text output]';
      }
    });
  }

  const anthropicKey = optional('ANTHROPIC_API_KEY');
  const anthropicModel = optional('ANTHROPIC_MODEL');
  if (anthropicKey && anthropicModel) {
    const client = new Anthropic({ apiKey: anthropicKey });
    participants.push({
      seat: 'CLAUDE',
      provider: 'anthropic',
      model: anthropicModel,
      async respond(input: string): Promise<string> {
        const message = await client.messages.create({
          model: anthropicModel,
          max_tokens: 4096,
          system:
            'You are the CLAUDE seat in BL-BRIDGE/1.0. Return concise explicit work products and rationale only. Do not expose hidden chain-of-thought. Preserve uncertainty, provenance, and dissent.',
          messages: [{ role: 'user', content: input }]
        });
        return message.content
          .filter((block) => block.type === 'text')
          .map((block) => block.text)
          .join('\n')
          .trim() || '[Claude returned no text output]';
      }
    });
  }

  const geminiKey = optional('GEMINI_API_KEY');
  const geminiModel = optional('GEMINI_MODEL');
  if (geminiKey && geminiModel) {
    const ai = new GoogleGenAI({ apiKey: geminiKey });
    participants.push({
      seat: 'GEMINI',
      provider: 'google',
      model: geminiModel,
      async respond(input: string): Promise<string> {
        const interaction = await ai.interactions.create({
          model: geminiModel,
          input
        });
        return interaction.output_text?.trim() || '[Gemini returned no text output]';
      }
    });
  }

  const deusEndpoint = optional('DEUS_ENDPOINT');
  if (deusEndpoint) {
    const deusToken = optional('DEUS_BRIDGE_TOKEN');
    const deusModel = optional('DEUS_RUNTIME_ID') ?? 'deus-runtime';
    participants.push({
      seat: 'DEUS',
      provider: 'deus-http',
      model: deusModel,
      async respond(input: string, roundId: string): Promise<string> {
        const response = await fetch(deusEndpoint, {
          method: 'POST',
          headers: {
            'content-type': 'application/json',
            ...(deusToken ? { authorization: `Bearer ${deusToken}` } : {})
          },
          body: JSON.stringify({
            protocol: 'BL-BRIDGE/1.0',
            round_id: roundId,
            seat: 'DEUS',
            input
          })
        });
        if (!response.ok) {
          throw new Error(`DEUS adapter HTTP ${response.status}: ${await response.text()}`);
        }
        const data = (await response.json()) as {
          output_text?: string;
          content?: string;
        };
        return (data.output_text ?? data.content ?? '').trim() || '[DEUS returned no text output]';
      }
    });
  }

  return participants;
}

export function providerProvenance(participant: Participant) {
  return {
    provider: participant.provider,
    model: participant.model,
    adapter_version: ADAPTER_VERSION,
    runtime_id: null,
    source_refs: []
  };
}

export function seat(participants: Participant[], target: Seat): Participant | undefined {
  return participants.find((participant) => participant.seat === target);
}

export { required };
