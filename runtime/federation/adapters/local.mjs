export class LocalAdapter {
  constructor(handlers = {}) { this.handlers = new Map(Object.entries(handlers)); }
  async execute(provider, task) {
    const handler = this.handlers.get(task.capability);
    if (!handler) throw new Error(`local capability not installed: ${task.capability}`);
    return handler(structuredClone(task.payload), { provider: structuredClone(provider), task: structuredClone(task) });
  }
}
