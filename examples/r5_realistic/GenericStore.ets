
export class GenericStore<T> {
  private data: T | null = null

  set(value: T): void {
    this.data = value
  }

  get(): T {
    return this.data as T
  }

  clear(): void {
    this.data = null
  }

  hasValue(): boolean {
    return this.data !== null
  }
}
