/**
 * ArkTS 示例项目 - 用于测试知识图谱系统
 * 模拟一个简单的鸿蒙应用项目结构
 */

// ==================== 入口组件 ====================
@Entry
@Component
export struct IndexPage {
    @State message: string = 'Hello World'
    @Link counter: number
    @Provide appName: string = 'ArkTS Demo'

    aboutToAppear() {
        console.log('IndexPage aboutToAppear')
        this.initData()
    }

    aboutToDisappear() {
        this.cleanup()
    }

    private initData() {
        this.message = 'Welcome to ArkTS'
        this.loadData()
    }

    private loadData() {
        const data = this.fetchData()
        this.processData(data)
    }

    private fetchData(): string {
        return 'sample data'
    }

    private processData(data: string) {
        console.log(data)
    }

    private cleanup() {
        console.log('cleanup')
    }

    build() {
        Column() {
            Text(this.message)
                .fontSize(20)
                .onClick(() => {
                    this.handleClick()
                })

            Button('Click Me')
                .onClick(() => {
                    this.incrementCounter()
                })

            if (this.counter > 0) {
                Text(`Counter: ${this.counter}`)
            }

            ForEach([1, 2, 3], (item: number) => {
                Text(`Item ${item}`)
            })
        }
    }

    private handleClick() {
        this.message = 'Clicked!'
        this.logEvent('click')
    }

    private incrementCounter() {
        this.counter++
        this.updateUI()
    }

    private updateUI() {
        console.log('UI updated')
    }

    private logEvent(event: string) {
        console.log(`Event: ${event}`)
    }
}

// ==================== 服务层 ====================
export class UserService {
    private static instance: UserService
    private users: Map<string, string> = new Map()

    static getInstance(): UserService {
        if (!UserService.instance) {
            UserService.instance = new UserService()
        }
        return UserService.instance
    }

    async login(username: string, password: string): Promise<boolean> {
        const token = await this.authenticate(username, password)
        return token !== null
    }

    private async authenticate(user: string, pass: string): Promise<string | null> {
        if (user && pass) {
            return this.generateToken(user)
        }
        return null
    }

    private generateToken(user: string): string {
        return `token_${user}_${Date.now()}`
    }

    async getUserInfo(userId: string): Promise<object> {
        const profile = await this.fetchProfile(userId)
        return this.formatProfile(profile)
    }

    private async fetchProfile(id: string): Promise<object> {
        return { id: id, name: 'Test User' }
    }

    private formatProfile(profile: object): object {
        return profile
    }

    logout(): void {
        this.users.clear()
    }
}

// ==================== 工具类 ====================
export class HttpUtil {
    private static baseUrl: string = 'https://api.example.com'

    static async get(url: string, params?: object): Promise<object> {
        const fullUrl = HttpUtil.buildUrl(url, params)
        const response = await HttpUtil.request(fullUrl, 'GET')
        return HttpUtil.parseResponse(response)
    }

    static async post(url: string, data: object): Promise<object> {
        const fullUrl = HttpUtil.buildUrl(url)
        const response = await HttpUtil.request(fullUrl, 'POST', data)
        return HttpUtil.parseResponse(response)
    }

    private static buildUrl(url: string, params?: object): string {
        return `${HttpUtil.baseUrl}${url}`
    }

    private static async request(url: string, method: string, data?: object): Promise<object> {
        return { url, method, data }
    }

    private static parseResponse(response: object): object {
        return response
    }
}

// ==================== 数据模型 ====================
export interface UserInfo {
    id: string
    name: string
    email: string
    avatar: string
}

export class BaseModel {
    protected id: string = ''
    protected createdAt: number = 0
    protected updatedAt: number = 0

    getId(): string {
        return this.id
    }

    setCreatedAt(timestamp: number): void {
        this.createdAt = timestamp
    }

    setUpdatedAt(timestamp: number): void {
        this.updatedAt = timestamp
    }

    toJSON(): object {
        return {
            id: this.id,
            createdAt: this.createdAt,
            updatedAt: this.updatedAt
        }
    }
}

export class UserModel extends BaseModel {
    private name: string = ''
    private email: string = ''

    constructor(name: string, email: string) {
        super()
        this.name = name
        this.email = email
    }

    getName(): string {
        return this.name
    }

    getEmail(): string {
        return this.email
    }

    override toJSON(): object {
        return {
            ...super.toJSON(),
            name: this.name,
            email: this.email
        }
    }
}

// ==================== 枚举 ====================
export enum PageStatus {
    LOADING = 'loading',
    SUCCESS = 'success',
    ERROR = 'error',
    EMPTY = 'empty'
}

export enum ThemeMode {
    LIGHT = 'light',
    DARK = 'dark',
    AUTO = 'auto'
}

// ==================== 自定义组件 ====================
@Component
export struct CustomButton {
    @Prop label: string = 'Button'
    @Prop disabled: boolean = false
    private onClickCallback: () => void = () => {}

    build() {
        Button(this.label)
            .enabled(!this.disabled)
            .onClick(() => {
                this.onClickCallback()
            })
    }
}

@Component
export struct UserCard {
    @Prop userName: string = ''
    @Prop userEmail: string = ''

    build() {
        Column() {
            Text(this.userName)
                .fontSize(16)
            Text(this.userEmail)
                .fontSize(12)
                .fontColor('#999')
        }
        .padding(12)
        .borderRadius(8)
    }
}

// ==================== 命名空间 ====================
namespace AppConstants {
    export const APP_VERSION: string = '1.0.0'
    export const API_TIMEOUT: number = 30000
    export const MAX_RETRY: number = 3
    export const CACHE_SIZE: number = 100
}

// ==================== 类型别名 ====================
type StringMap = Record<string, string>
type Callback = (data: object) => void
type AsyncCallback = (data: object) => Promise<void>
