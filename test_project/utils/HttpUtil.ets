/**
 * 工具类 - HTTP请求、存储、各种工具函数
 */

// HTTP工具类
export class HttpUtil {
    private static baseUrl: string = 'https://api.example.com'
    private static timeout: number = 30000
    private static headers: Record<string, string> = {
        'Content-Type': 'application/json'
    }

    static setBaseUrl(url: string): void {
        HttpUtil.baseUrl = url
    }

    static setHeader(key: string, value: string): void {
        HttpUtil.headers[key] = value
    }

    static setToken(token: string): void {
        HttpUtil.headers['Authorization'] = `Bearer ${token}`
    }

    static async get<T = any>(url: string, params?: Record<string, any>): Promise<T> {
        const fullUrl = HttpUtil.buildUrl(url, params)
        return HttpUtil.request<T>(fullUrl, 'GET')
    }

    static async post<T = any>(url: string, data?: any): Promise<T> {
        const fullUrl = HttpUtil.buildUrl(url)
        return HttpUtil.request<T>(fullUrl, 'POST', data)
    }

    static async put<T = any>(url: string, data?: any): Promise<T> {
        const fullUrl = HttpUtil.buildUrl(url)
        return HttpUtil.request<T>(fullUrl, 'PUT', data)
    }

    static async delete<T = any>(url: string): Promise<T> {
        const fullUrl = HttpUtil.buildUrl(url)
        return HttpUtil.request<T>(fullUrl, 'DELETE')
    }

    private static buildUrl(url: string, params?: Record<string, any>): string {
        let fullUrl = url.startsWith('http') ? url : `${HttpUtil.baseUrl}${url}`
        if (params) {
            const query = Object.entries(params)
                .filter(([_, v]) => v !== undefined && v !== null)
                .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
                .join('&')
            if (query) {
                fullUrl += `?${query}`
            }
        }
        return fullUrl
    }

    private static async request<T>(url: string, method: string, data?: any): Promise<T> {
        // 模拟请求
        console.log(`HTTP ${method} ${url}`, data)
        return {} as T
    }
}

// 存储工具类
export class StorageUtil {
    private static storage: Map<string, any> = new Map()

    static set(key: string, value: any): void {
        StorageUtil.storage.set(key, value)
    }

    static get(key: string): any {
        return StorageUtil.storage.get(key)
    }

    static remove(key: string): void {
        StorageUtil.storage.delete(key)
    }

    static has(key: string): boolean {
        return StorageUtil.storage.has(key)
    }

    static clear(): void {
        StorageUtil.storage.clear()
    }

    static keys(): string[] {
        return Array.from(StorageUtil.storage.keys())
    }

    static size(): number {
        return StorageUtil.storage.size
    }

    static getJSON<T>(key: string): T | null {
        const value = StorageUtil.storage.get(key)
        if (typeof value === 'string') {
            try {
                return JSON.parse(value) as T
            } catch {
                return null
            }
        }
        return null
    }

    static setJSON<T>(key: string, value: T): void {
        StorageUtil.storage.set(key, JSON.stringify(value))
    }
}

// 日期工具类
export class DateUtil {
    static format(date: Date | number, format: string = 'YYYY-MM-DD HH:mm:ss'): string {
        const d = typeof date === 'number' ? new Date(date) : date
        const year = d.getFullYear()
        const month = String(d.getMonth() + 1).padStart(2, '0')
        const day = String(d.getDate()).padStart(2, '0')
        const hours = String(d.getHours()).padStart(2, '0')
        const minutes = String(d.getMinutes()).padStart(2, '0')
        const seconds = String(d.getSeconds()).padStart(2, '0')

        return format
            .replace('YYYY', String(year))
            .replace('MM', month)
            .replace('DD', day)
            .replace('HH', hours)
            .replace('mm', minutes)
            .replace('ss', seconds)
    }

    static parse(dateString: string): Date {
        return new Date(dateString)
    }

    static now(): number {
        return Date.now()
    }

    static addDays(date: Date, days: number): Date {
        const result = new Date(date)
        result.setDate(result.getDate() + days)
        return result
    }

    static addMonths(date: Date, months: number): Date {
        const result = new Date(date)
        result.setMonth(result.getMonth() + months)
        return result
    }

    static diffInDays(date1: Date, date2: Date): number {
        const diff = date1.getTime() - date2.getTime()
        return Math.floor(diff / (1000 * 60 * 60 * 24))
    }

    static isToday(date: Date): boolean {
        const today = new Date()
        return date.toDateString() === today.toDateString()
    }

    static isThisWeek(date: Date): boolean {
        const today = new Date()
        const startOfWeek = new Date(today)
        startOfWeek.setDate(today.getDate() - today.getDay())
        startOfWeek.setHours(0, 0, 0, 0)
        return date >= startOfWeek
    }

    static isThisMonth(date: Date): boolean {
        const today = new Date()
        return date.getMonth() === today.getMonth() && date.getFullYear() === today.getFullYear()
    }
}

// 字符串工具类
export class StringUtil {
    static isEmpty(value: string | null | undefined): boolean {
        return value === null || value === undefined || value.trim() === ''
    }

    static isNotEmpty(value: string | null | undefined): boolean {
        return !StringUtil.isEmpty(value)
    }

    static truncate(value: string, maxLength: number, suffix: string = '...'): string {
        if (value.length <= maxLength) return value
        return value.substring(0, maxLength - suffix.length) + suffix
    }

    static capitalize(value: string): string {
        if (!value) return value
        return value.charAt(0).toUpperCase() + value.slice(1)
    }

    static camelCase(value: string): string {
        return value
            .toLowerCase()
            .replace(/[-_\s]+(.)?/g, (_, c) => (c ? c.toUpperCase() : ''))
    }

    static kebabCase(value: string): string {
        return value
            .replace(/([a-z])([A-Z])/g, '$1-$2')
            .replace(/[\s_]+/g, '-')
            .toLowerCase()
    }

    static snakeCase(value: string): string {
        return value
            .replace(/([a-z])([A-Z])/g, '$1_$2')
            .replace(/[\s-]+/g, '_')
            .toLowerCase()
    }

    static random(length: number = 16): string {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
        let result = ''
        for (let i = 0; i < length; i++) {
            result += chars.charAt(Math.floor(Math.random() * chars.length))
        }
        return result
    }

    static mask(value: string, start: number = 0, end: number = value.length, maskChar: string = '*'): string {
        if (start >= end || start < 0 || end > value.length) return value
        return value.substring(0, start) + maskChar.repeat(end - start) + value.substring(end)
    }
}

// 数组工具类
export class ArrayUtil {
    static isEmpty<T>(arr: T[] | null | undefined): boolean {
        return !arr || arr.length === 0
    }

    static isNotEmpty<T>(arr: T[] | null | undefined): boolean {
        return !ArrayUtil.isEmpty(arr)
    }

    static unique<T>(arr: T[]): T[] {
        return [...new Set(arr)]
    }

    static uniqueBy<T, K>(arr: T[], keyFn: (item: T) => K): T[] {
        const seen = new Set<K>()
        return arr.filter(item => {
            const key = keyFn(item)
            if (seen.has(key)) return false
            seen.add(key)
            return true
        })
    }

    static groupBy<T, K extends string | number>(arr: T[], keyFn: (item: T) => K): Record<K, T[]> {
        return arr.reduce((acc, item) => {
            const key = keyFn(item)
            if (!acc[key]) acc[key] = []
            acc[key].push(item)
            return acc
        }, {} as Record<K, T[]>)
    }

    static chunk<T>(arr: T[], size: number): T[][] {
        const result: T[][] = []
        for (let i = 0; i < arr.length; i += size) {
            result.push(arr.slice(i, i + size))
        }
        return result
    }

    static flatten<T>(arr: (T | T[])[]): T[] {
        return arr.reduce<T[]>((acc, item) => {
            return acc.concat(Array.isArray(item) ? item : [item])
        }, [])
    }

    static sortBy<T>(arr: T[], keyFn: (item: T) => number | string, desc: boolean = false): T[] {
        const sorted = [...arr].sort((a, b) => {
            const va = keyFn(a)
            const vb = keyFn(b)
            if (typeof va === 'string' && typeof vb === 'string') {
                return va.localeCompare(vb)
            }
            return (va as number) - (vb as number)
        })
        return desc ? sorted.reverse() : sorted
    }

    static sum(arr: number[]): number {
        return arr.reduce((sum, n) => sum + n, 0)
    }

    static average(arr: number[]): number {
        return arr.length > 0 ? ArrayUtil.sum(arr) / arr.length : 0
    }

    static min(arr: number[]): number | undefined {
        return arr.length > 0 ? Math.min(...arr) : undefined
    }

    static max(arr: number[]): number | undefined {
        return arr.length > 0 ? Math.max(...arr) : undefined
    }
}

// 对象工具类
export class ObjectUtil {
    static isEmpty(obj: object | null | undefined): boolean {
        if (!obj) return true
        return Object.keys(obj).length === 0
    }

    static clone<T extends object>(obj: T): T {
        return { ...obj }
    }

    static deepClone<T>(obj: T): T {
        return JSON.parse(JSON.stringify(obj))
    }

    static merge<T extends object>(target: T, ...sources: Partial<T>[]): T {
        return Object.assign({}, target, ...sources)
    }

    static pick<T extends object, K extends keyof T>(obj: T, keys: K[]): Pick<T, K> {
        const result = {} as Pick<T, K>
        keys.forEach(key => {
            if (key in obj) {
                result[key] = obj[key]
            }
        })
        return result
    }

    static omit<T extends object, K extends keyof T>(obj: T, keys: K[]): Omit<T, K> {
        const result = { ...obj }
        keys.forEach(key => delete result[key])
        return result
    }

    static get<T = any>(obj: any, path: string, defaultValue?: T): T | undefined {
        const keys = path.split('.')
        let result = obj
        for (const key of keys) {
            if (result === null || result === undefined) {
                return defaultValue
            }
            result = result[key]
        }
        return result ?? defaultValue
    }

    static set<T extends object>(obj: T, path: string, value: any): T {
        const keys = path.split('.')
        let current: any = obj
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i]
            if (!(key in current)) {
                current[key] = {}
            }
            current = current[key]
        }
        current[keys[keys.length - 1]] = value
        return obj
    }
}
