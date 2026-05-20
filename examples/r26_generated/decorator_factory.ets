
function Log(prefix: string): MethodDecorator {
  return function(target: Object, key: string, descriptor: TypedPropertyDescriptor<any>) {
    const original = descriptor.value
    descriptor.value = function(...args: any[]) {
      console.info(`${prefix}: ${key} called`)
      return original.apply(this, args)
    }
    return descriptor
  }
}

function Memoize(): MethodDecorator {
  return function(target: Object, key: string, descriptor: TypedPropertyDescriptor<any>) {
    const original = descriptor.value
    const cache = new Map<string, any>()
    descriptor.value = function(...args: any[]) {
      const cacheKey = JSON.stringify(args)
      if (cache.has(cacheKey)) {
        return cache.get(cacheKey)
      }
      const result = original.apply(this, args)
      cache.set(cacheKey, result)
      return result
    }
    return descriptor
  }
}

class DecoratedService {
  @Log('Service')
  @Memoize()
  expensiveOperation(n: number): number {
    return n * n
  }
  
  @Log('Service')
  anotherMethod(s: string): string {
    return s.toUpperCase()
  }
}
