/**
 * 服务层 - 测试复杂继承、单例模式、异步方法
 */

import { HttpUtil, StorageUtil } from '../utils/HttpUtil'
import type { UserInfo, UserConfig } from './Types'

// 单例基类
abstract class Singleton<T> {
    private static instances: Map<string, any> = new Map()

    protected constructor() {}

    static getInstance<T>(this: new () => T): T {
        const className = this.name
        if (!Singleton.instances.has(className)) {
            Singleton.instances.set(className, new this())
        }
        return Singleton.instances.get(className)
    }

    static clearInstance(className: string): void {
        Singleton.instances.delete(className)
    }
}

// 用户服务
export class UserService extends Singleton<UserService> {
    private cache: Map<string, UserInfo> = new Map()
    private pendingRequests: Map<string, Promise<UserInfo>> = new Map()
    private initialized: boolean = false

    private constructor() {
        super()
    }

    static override getInstance(): UserService {
        return super.getInstance.call(UserService)
    }

    async initialize(): Promise<void> {
        if (this.initialized) return
        await this.loadCache()
        this.initialized = true
    }

    private async loadCache(): Promise<void> {
        const cached = StorageUtil.get('userCache') as string
        if (cached) {
            const users = JSON.parse(cached) as UserInfo[]
            users.forEach(u => this.cache.set(u.id, u))
        }
    }

    async fetchUserInfo(token: string): Promise<{ users: UserInfo[], config: UserConfig }> {
        const response = await HttpUtil.get('/api/users', { token })
        return this.parseResponse(response)
    }

    private parseResponse(response: any): { users: UserInfo[], config: UserConfig } {
        return {
            users: response.users || [],
            config: response.config || {}
        }
    }

    async getUserById(id: string): Promise<UserInfo | null> {
        // 检查缓存
        if (this.cache.has(id)) {
            return this.cache.get(id)!
        }

        // 检查是否有进行中的请求（防止重复请求）
        if (this.pendingRequests.has(id)) {
            return this.pendingRequests.get(id)!
        }

        // 发起新请求
        const promise = this.fetchUserFromServer(id)
        this.pendingRequests.set(id, promise)

        try {
            const user = await promise
            if (user) {
                this.cache.set(id, user)
            }
            return user
        } finally {
            this.pendingRequests.delete(id)
        }
    }

    private async fetchUserFromServer(id: string): Promise<UserInfo | null> {
        try {
            const response = await HttpUtil.get(`/api/users/${id}`)
            return response as UserInfo
        } catch (error) {
            console.error(`Failed to fetch user ${id}:`, error)
            return null
        }
    }

    async preloadCache(): Promise<void> {
        const users = await this.fetchAllUsers()
        users.forEach(u => this.cache.set(u.id, u))
        this.saveCache()
    }

    private async fetchAllUsers(): Promise<UserInfo[]> {
        const response = await HttpUtil.get('/api/users/all')
        return (response as any[]).map(this.mapToUserInfo)
    }

    private mapToUserInfo(data: any): UserInfo {
        return {
            id: data.id,
            name: data.name,
            email: data.email,
            avatar: data.avatar,
            createdAt: data.created_at,
            updatedAt: data.updated_at
        }
    }

    private saveCache(): void {
        const users = Array.from(this.cache.values())
        StorageUtil.set('userCache', JSON.stringify(users))
    }

    clearCache(): void {
        this.cache.clear()
        StorageUtil.remove('userCache')
    }

    getCacheSize(): number {
        return this.cache.size
    }
}

// 认证服务
export class AuthService extends Singleton<AuthService> {
    private token: string | null = null
    private refreshToken: string | null = null
    private expiresAt: number = 0

    private constructor() {
        super()
        this.loadStoredTokens()
    }

    private loadStoredTokens(): void {
        this.token = StorageUtil.get('authToken') as string
        this.refreshToken = StorageUtil.get('refreshToken') as string
        const expires = StorageUtil.get('tokenExpires') as string
        this.expiresAt = expires ? parseInt(expires) : 0
    }

    async login(username: string, password: string): Promise<boolean> {
        try {
            const response = await HttpUtil.post('/api/auth/login', {
                username,
                password
            })

            this.setTokens(
                response.access_token,
                response.refresh_token,
                response.expires_in
            )

            return true
        } catch (error) {
            console.error('Login failed:', error)
            return false
        }
    }

    async logout(): Promise<void> {
        try {
            await HttpUtil.post('/api/auth/logout', {})
        } catch (error) {
            console.error('Logout failed:', error)
        } finally {
            this.clearTokens()
        }
    }

    private setTokens(accessToken: string, refreshToken: string, expiresIn: number): void {
        this.token = accessToken
        this.refreshToken = refreshToken
        this.expiresAt = Date.now() + expiresIn * 1000

        StorageUtil.set('authToken', accessToken)
        StorageUtil.set('refreshToken', refreshToken)
        StorageUtil.set('tokenExpires', this.expiresAt.toString())
    }

    private clearTokens(): void {
        this.token = null
        this.refreshToken = null
        this.expiresAt = 0

        StorageUtil.remove('authToken')
        StorageUtil.remove('refreshToken')
        StorageUtil.remove('tokenExpires')
    }

    getToken(): string | null {
        if (this.isTokenExpired()) {
            return null
        }
        return this.token
    }

    private isTokenExpired(): boolean {
        if (!this.token) return true
        return Date.now() >= this.expiresAt - 60000 // 提前1分钟判断过期
    }

    async refreshAccessToken(): Promise<boolean> {
        if (!this.refreshToken) return false

        try {
            const response = await HttpUtil.post('/api/auth/refresh', {
                refresh_token: this.refreshToken
            })

            this.setTokens(
                response.access_token,
                response.refresh_token,
                response.expires_in
            )

            return true
        } catch (error) {
            console.error('Token refresh failed:', error)
            this.clearTokens()
            return false
        }
    }

    isAuthenticated(): boolean {
        return !!this.getToken()
    }
}

// 事件总线
export class EventBus {
    private static instance: EventBus
    private listeners: Map<string, Set<Function>> = new Map()

    private constructor() {}

    static getInstance(): EventBus {
        if (!EventBus.instance) {
            EventBus.instance = new EventBus()
        }
        return EventBus.instance
    }

    on(event: string, callback: Function): void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set())
        }
        this.listeners.get(event)!.add(callback)
    }

    off(event: string, callback: Function): void {
        this.listeners.get(event)?.delete(callback)
    }

    emit(event: string, data?: any): void {
        this.listeners.get(event)?.forEach(callback => {
            try {
                callback(data)
            } catch (error) {
                console.error(`Error in event handler for ${event}:`, error)
            }
        })
    }

    once(event: string, callback: Function): void {
        const wrapper = (data: any) => {
            callback(data)
            this.off(event, wrapper)
        }
        this.on(event, wrapper)
    }

    clear(): void {
        this.listeners.clear()
    }
}

// 数据验证器
export class Validator {
    static isEmail(value: string): boolean {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
    }

    static isPhone(value: string): boolean {
        return /^1[3-9]\d{9}$/.test(value)
    }

    static isUrl(value: string): boolean {
        try {
            new URL(value)
            return true
        } catch {
            return false
        }
    }

    static isNotEmpty(value: string | null | undefined): boolean {
        return value !== null && value !== undefined && value.trim() !== ''
    }

    static minLength(value: string, min: number): boolean {
        return value.length >= min
    }

    static maxLength(value: string, max: number): boolean {
        return value.length <= max
    }

    static inRange(value: number, min: number, max: number): boolean {
        return value >= min && value <= max
    }

    static isOneOf<T>(value: T, options: T[]): boolean {
        return options.includes(value)
    }
}

// 日志服务
export class Logger {
    private static instance: Logger
    private level: 'debug' | 'info' | 'warn' | 'error' = 'info'
    private logs: Array<{ level: string; message: string; timestamp: number }> = []

    private constructor() {}

    static getInstance(): Logger {
        if (!Logger.instance) {
            Logger.instance = new Logger()
        }
        return Logger.instance
    }

    setLevel(level: 'debug' | 'info' | 'warn' | 'error'): void {
        this.level = level
    }

    debug(message: string, ...args: any[]): void {
        this.log('debug', message, args)
    }

    info(message: string, ...args: any[]): void {
        this.log('info', message, args)
    }

    warn(message: string, ...args: any[]): void {
        this.log('warn', message, args)
    }

    error(message: string, ...args: any[]): void {
        this.log('error', message, args)
    }

    private log(level: string, message: string, args: any[]): void {
        const levels = ['debug', 'info', 'warn', 'error']
        if (levels.indexOf(level) >= levels.indexOf(this.level)) {
            const timestamp = new Date().toISOString()
            console.log(`[${timestamp}] [${level.toUpperCase()}] ${message}`, ...args)
            this.logs.push({ level, message, timestamp: Date.now() })
        }
    }

    getLogs(): Array<{ level: string; message: string; timestamp: number }> {
        return [...this.logs]
    }

    clearLogs(): void {
        this.logs = []
    }
}
