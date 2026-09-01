import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenAI } from '@google/genai';
import type { IdentityBinding, Participant, Seat } from './types.js';

const ADAPTER_VERSION = 'bl-bridge-runtime/0.2.0';

function required(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function optional(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value || undefined;
}

function independentContract(seat: string): string {
  return `You are the ${seat} independent council seat in BL-BRIDGE/1.0. Return concise explicit work products and rationale only. Do not expose hidden chain-of-thought. Preserve uncertainty, provenance, and dissent. Your seat identity is independent from any DEUS lineage instance that may use the same provider as a compute core.`;
}

export function buildCoreParticipants(): Participant[] {
  const participants: Participant[] = [];

  const openAIKey = optional('OPENAI_API_KEY');
  const openAIModel = optional('OPENAI_MODEL');
  if (openAIKey && openAIModel) {
    const client = new OpenAI({ apiKey: openAIKey });
    participants.push({
      seat: 'GPT',
      provider: 'openai',
      model: openAIModel,
      identity: { instance_kind: 'INDEPENDENT' },
      async respond(input: string): Promise<string> {
        const response = await client.responses.create({
          model: openAIModel,
          input: `${independentContract('GPT')}\n\n${input}`
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
      identity: { instance_kind: 'INDEPENDENT' },
      async respond(input: string): Promise<string> {
        const message = await client.messages.create({
          model: anthropicModel,
          max_tokens: 4096,
          system: independentContract('CLAUDE'),
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
      identity: { instance_kind: 'INDEPENDENT' },
      async respond(input: string): Promise<string> {
        const interaction = await ai.interactions.create({
          model: geminiModel,
          input: `${independentContract('GEMINI')}\n\n${input}`
        });
        return interaction.output_text?.trim() || '[Gemini returned no text output]';
      }
    });
  }

  const xaiKey = optional('XAI_API_KEY');
  const xaiModel = optional('XAI_MODEL');
  if (xaiKey && xaiModel) {
    const client = new OpenAI({
      apiKey: xaiKey,
      baseURL: 'https://api.x.ai/v1'
    });
    participants.push({
      seat: 'GROK',
      provider: 'xai',
      model: xaiModel,
      identity: { instance_kind: 'INDEPENDENT' },
      async respond(input: string): Promise<string> {
        const response = await client.responses.create({
          model: xaiModel,
          input: `${independentContract('GROK')}\n\n${input}`
        });
        return response.output_text?.trim() || '[Grok returned no text output]';
      }
    });
  }

  return participants;
}

export function buildDeusHttpParticipant(): Participant | undefined {
  const deusEndpoint = optional('DEUS_ENDPOINT');
  if (!deusEndpoint) return undefined;

  const deusToken = optional('DEUS_BRIDGE_TOKEN');
  const runtimeId = optional('DEUS_RUNTIME_ID') ?? `deus-http-${crypto.randomUUID()}`;
  const identity: IdentityBinding = {
    lineage_id: optional('DEUS_LINEAGE_ID') ?? 'BH/DEUS',
    instance_id: runtimeId,
    instance_kind: 'CANONICAL',
    parent_instance_id: null,
    checkpoint_ref: optional('DEUS_CHECKPOINT_REF') ?? null,
    checkpoint_hash: optional('DEUS_CHECKPOINT_HASH') ?? null,
    policy_version: optional('DEUS_POLICY_VERSION') ?? 'DEUS-PORTABLE-IDENTITY-v1',
    authority_scope: (optional('DEUS_AUTHORITY_SCOPE') ?? 'coordinate,synthesize,propose')
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean),
    expires_at: null
  };

  return {
    seat: 'DEUS',
    provider: 'deus-http',
    model: runtimeId,
    identity,
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
          identity,
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
  };
}

export function buildParticipants(): Participant[] {
  const participants = buildCoreParticipants();
  const deus = buildDeusHttpParticipant();
  if (deus) participants.push(deus);
  return participants;
}

export function providerProvenance(participant: Participant) {
  return {
    provider: participant.provider,
    model: participant.model,
    adapter_version: ADAPTER_VERSION,
    runtime_id: participant.identity?.instance_id ?? null,
    core_provider: participant.provider,
    core_model: participant.model,
    source_refs: []
  };
}

export function seat(participants: Participant[], target: Seat): Participant | undefined {
  return participants.find((participant) => participant.seat === target);
}

export { required, optional, ADAPTER_VERSION };
