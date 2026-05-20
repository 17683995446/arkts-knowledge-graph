
class Repository<T> {
  private items: T[] = []
  
  add(item: T): void {
    this.items.push(item)
  }
  
  remove(predicate: (item: T) => boolean): void {
    this.items = this.items.filter(item => !predicate(item))
  }
  
  find(predicate: (item: T) => boolean): T | undefined {
    return this.items.find(predicate)
  }
  
  findAll(predicate?: (item: T) => boolean): T[] {
    if (predicate) {
      return this.items.filter(predicate)
    }
    return [...this.items]
  }
  
  count(): number {
    return this.items.length
  }
  
  clear(): void {
    this.items = []
  }
}

class CachedRepository<T> extends Repository<T> {
  private cache: Map<string, T[]> = new Map()
  private cacheKey: string = ''
  
  setCacheKey(key: string): void {
    this.cacheKey = key
  }
  
  invalidateCache(): void {
    this.cache.delete(this.cacheKey)
  }
  
  getFromCache(): T[] | undefined {
    return this.cache.get(this.cacheKey)
  }
}
