/**
 * 复杂语法测试文件
 * 包含各种ArkTS高级特性
 */

// ==================== 泛型测试 ====================

// 泛型接口
interface Repository<T, K = string> {
    findById(id: K): Promise<T | null>
    findAll(): Promise<T[]>
    save(entity: T): Promise<void>
    delete(id: K): Promise<boolean>
}

// 泛型类
class CacheManager<T extends { id: string }> {
    private cache: Map<string, T> = new Map()
    private ttl: number
    
    constructor(ttl: number = 60000) {
        this.ttl = ttl
    }
    
    get(key: string): T | undefined {
        return this.cache.get(key)
    }
    
    set(key: string, value: T): void {
        this.cache.set(key, value)
    }
    
    has(key: string): boolean {
        return this.cache.has(key)
    }
    
    clear(): void {
        this.cache.clear()
    }
}

// 泛型约束
interface WithId {
    id: string
}

class EntityService<T extends WithId> {
    protected entities: Map<string, T> = new Map()
    
    add(entity: T): void {
        this.entities.set(entity.id, entity)
    }
    
    get(id: string): T | undefined {
        return this.entities.get(id)
    }
    
    getAll(): T[] {
        return Array.from(this.entities.values())
    }
}

// ==================== 装饰器测试 ====================

function Log(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const original = descriptor.value
    descriptor.value = function(...args: any[]) {
        console.log(`Calling ${propertyKey} with args:`, args)
        return original.apply(this, args)
    }
}

function Memoize(ttl: number = 60000) {
    return function(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
        const original = descriptor.value
        const cache = new Map<string, { value: any, timestamp: number }>()
        
        descriptor.value = function(...args: any[]) {
            const key = JSON.stringify(args)
            const cached = cache.get(key)
            
            if (cached && Date.now() - cached.timestamp < ttl) {
                return cached.value
            }
            
            const result = original.apply(this, args)
            cache.set(key, { value: result, timestamp: Date.now() })
            return result
        }
    }
}

// ==================== 异步测试 ====================

class AsyncDataService {
    private data: Map<string, any> = new Map()
    
    async fetchData<T>(url: string): Promise<T> {
        // 模拟异步请求
        return new Promise((resolve, reject) => {
            setTimeout(() => {
                const cached = this.data.get(url)
                if (cached) {
                    resolve(cached as T)
                } else {
                    reject(new Error('Not found'))
                }
            }, 100)
        })
    }
    
    async batchFetch<T>(urls: string[]): Promise<T[]> {
        const promises = urls.map(url => this.fetchData<T>(url))
        return Promise.all(promises)
    }
    
    async *streamData(count: number): AsyncGenerator<{ index: number, data: string }> {
        for (let i = 0; i < count; i++) {
            await new Promise(resolve => setTimeout(resolve, 10))
            yield { index: i, data: `Item ${i}` }
        }
    }
}

// ==================== 复杂类型测试 ====================

type Partial<T> = {
    [P in keyof T]?: T[P]
}

type Required<T> = {
    [P in keyof T]-?: T[P]
}

type Readonly<T> = {
    readonly [P in keyof T]: T[P]
}

type Pick<T, K extends keyof T> = {
    [P in K]: T[P]
}

type Omit<T, K extends keyof T> = Pick<T, Exclude<keyof T, K>>

type Record<K extends string, T> = {
    [P in K]: T
}

// 条件类型
type NonNullable<T> = T extends null | undefined ? never : T

type ReturnType<T extends (...args: any) => any> = T extends (...args: any) => infer R ? R : any

type Parameters<T extends (...args: any) => any> = T extends (...args: infer P) => any ? P : never

// ==================== 命名空间测试 ====================

namespace Utils {
    export function debounce(fn: Function, delay: number): Function {
        let timer: number | null = null
        return function(this: any, ...args: any[]) {
            if (timer) clearTimeout(timer)
            timer = setTimeout(() => fn.apply(this, args), delay)
        }
    }
    
    export function throttle(fn: Function, limit: number): Function {
        let inThrottle = false
        return function(this: any, ...args: any[]) {
            if (!inThrottle) {
                fn.apply(this, args)
                inThrottle = true
                setTimeout(() => inThrottle = false, limit)
            }
        }
    }
    
    export namespace Math {
        export function clamp(value: number, min: number, max: number): number {
            return Math.max(min, Math.min(max, value))
        }
        
        export function lerp(a: number, b: number, t: number): number {
            return a + (b - a) * t
        }
    }
}

// ==================== 枚举测试 ====================

enum Status {
    PENDING = 'PENDING',
    PROCESSING = 'PROCESSING',
    COMPLETED = 'COMPLETED',
    FAILED = 'FAILED'
}

const enum Priority {
    LOW = 0,
    MEDIUM = 1,
    HIGH = 2,
    CRITICAL = 3
}

// ==================== 混合类测试 ====================

interface Printable {
    print(): void
}

interface Serializable {
    serialize(): string
}

class Document implements Printable, Serializable {
    constructor(
        public title: string,
        public content: string,
        public createdAt: Date = new Date()
    ) {}
    
    print(): void {
        console.log(`${this.title}\n${this.content}`)
    }
    
    serialize(): string {
        return JSON.stringify({
            title: this.title,
            content: this.content,
            createdAt: this.createdAt.toISOString()
        })
    }
    
    static fromJSON(json: string): Document {
        const data = JSON.parse(json)
        return new Document(data.title, data.content, new Date(data.createdAt))
    }
}

// ==================== 抽象类测试 ====================

abstract class BaseComponent {
    protected _state: Map<string, any> = new Map()
    
    abstract render(): string
    
    setState(key: string, value: any): void {
        this._state.set(key, value)
    }
    
    getState<T>(key: string): T | undefined {
        return this._state.get(key) as T
    }
    
    protected log(message: string): void {
        console.log(`[${this.constructor.name}] ${message}`)
    }
}

class ButtonComponent extends BaseComponent {
    constructor(
        public label: string,
        public onClick: () => void
    ) {
        super()
    }
    
    render(): string {
        return `<button onclick="${this.onClick}">${this.label}</button>`
    }
}

class InputComponent extends BaseComponent {
    constructor(
        public placeholder: string = '',
        public type: string = 'text'
    ) {
        super()
    }
    
    render(): string {
        return `<input type="${this.type}" placeholder="${this.placeholder}" />`
    }
}

// ==================== 代理测试 ====================

class ReactiveObject {
    private _data: Record<string, any> = {}
    private _listeners: Map<string, Set<Function>> = new Map()
    
    get(key: string): any {
        return this._data[key]
    }
    
    set(key: string, value: any): void {
        const oldValue = this._data[key]
        this._data[key] = value
        this._notify(key, value, oldValue)
    }
    
    watch(key: string, callback: Function): void {
        if (!this._listeners.has(key)) {
            this._listeners.set(key, new Set())
        }
        this._listeners.get(key)!.add(callback)
    }
    
    private _notify(key: string, newValue: any, oldValue: any): void {
        this._listeners.get(key)?.forEach(cb => cb(newValue, oldValue))
    }
}

// ==================== 导出 ====================

export {
    Repository,
    CacheManager,
    EntityService,
    AsyncDataService,
    Document,
    BaseComponent,
    ButtonComponent,
    InputComponent,
    ReactiveObject,
    Status,
    Priority,
    Utils
}
