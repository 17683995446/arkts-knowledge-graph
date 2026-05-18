/**
 * 示例项目 - 第二个文件
 * 模拟更多类和调用关系
 */

import { UserService, HttpUtil, UserInfo, PageStatus } from './MainPage'

// ==================== 列表页 ====================
@Entry
@Component
export struct ListPage {
    @State items: string[] = []
    @State status: PageStatus = PageStatus.LOADING
    private service: UserService = UserService.getInstance()

    async aboutToAppear() {
        await this.loadItems()
    }

    private async loadItems() {
        this.status = PageStatus.LOADING
        try {
            const result = await this.service.getUserInfo('123')
            this.items = this.parseItems(result)
            this.status = PageStatus.SUCCESS
        } catch (error) {
            this.status = PageStatus.ERROR
            this.handleError(error)
        }
    }

    private parseItems(data: object): string[] {
        return Object.keys(data)
    }

    private handleError(error: object) {
        console.error('Load failed:', error)
    }

    build() {
        Column() {
            if (this.status === PageStatus.LOADING) {
                Text('Loading...')
            } else if (this.status === PageStatus.ERROR) {
                Text('Error occurred')
            } else {
                List() {
                    ForEach(this.items, (item: string) => {
                        ListItem() {
                            Text(item)
                        }
                    })
                }
            }
        }
    }
}

// ==================== 网络请求管理器 ====================
export class NetworkManager {
    private static instance: NetworkManager
    private token: string = ''
    private retryCount: number = 0

    static getInstance(): NetworkManager {
        if (!NetworkManager.instance) {
            NetworkManager.instance = new NetworkManager()
        }
        return NetworkManager.instance
    }

    setToken(token: string): void {
        this.token = token
    }

    async request(url: string, method: string, data?: object): Promise<object> {
        try {
            const response = await HttpUtil.post(url, data || {})
            return this.handleResponse(response)
        } catch (error) {
            return this.handleRequestError(error, url)
        }
    }

    private handleResponse(response: object): object {
        return response
    }

    private async handleRequestError(error: object, url: string): Promise<object> {
        if (this.retryCount < AppConstants.MAX_RETRY) {
            this.retryCount++
            await this.delay(1000)
            return this.request(url, 'GET')
        }
        throw error
    }

    private delay(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms))
    }
}

// ==================== 数据存储 ====================
export class DataStorage {
    private cache: Map<string, object> = new Map()
    private maxSize: number = 100

    set(key: string, value: object): void {
        if (this.cache.size >= this.maxSize) {
            this.evictOldest()
        }
        this.cache.set(key, value)
    }

    get(key: string): object | null {
        return this.cache.get(key) || null
    }

    private evictOldest(): void {
        const firstKey = this.cache.keys().next().value
        if (firstKey) {
            this.cache.delete(firstKey)
        }
    }

    clear(): void {
        this.cache.clear()
    }

    size(): number {
        return this.cache.size
    }
}

// ==================== 事件总线 ====================
export class EventBus {
    private static instance: EventBus
    private listeners: Map<string, Array<Callback>> = new Map()

    static getInstance(): EventBus {
        if (!EventBus.instance) {
            EventBus.instance = new EventBus()
        }
        return EventBus.instance
    }

    on(event: string, callback: Callback): void {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, [])
        }
        this.listeners.get(event)!.push(callback)
    }

    off(event: string, callback: Callback): void {
        const cbs = this.listeners.get(event)
        if (cbs) {
            const index = cbs.indexOf(callback)
            if (index > -1) {
                cbs.splice(index, 1)
            }
        }
    }

    emit(event: string, data: object): void {
        const cbs = this.listeners.get(event)
        if (cbs) {
            cbs.forEach(cb => cb(data))
        }
    }

    clear(): void {
        this.listeners.clear()
    }
}
