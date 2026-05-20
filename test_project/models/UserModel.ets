/**
 * 数据模型 - 测试类继承、接口实现、装饰器
 */

// 基础实体接口
export interface IEntity {
    id: string
    createdAt: number
    updatedAt: number
    toJSON(): object
}

// 基础模型类
export class BaseModel implements IEntity {
    id: string = ''
    createdAt: number = Date.now()
    updatedAt: number = Date.now()

    constructor(data?: Partial<BaseModel>) {
        if (data) {
            Object.assign(this, data)
        }
    }

    touch(): void {
        this.updatedAt = Date.now()
    }

    toJSON(): object {
        return {
            id: this.id,
            createdAt: this.createdAt,
            updatedAt: this.updatedAt
        }
    }

    static fromJSON<T extends BaseModel>(this: new () => T, json: object): T {
        const instance = new this()
        Object.assign(instance, json)
        return instance
    }
}

// 用户信息接口
export interface UserInfo extends IEntity {
    name: string
    email: string
    avatar?: string
    phone?: string
    status: UserStatus
}

// 用户状态枚举
export enum UserStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    PENDING = 'pending',
    DELETED = 'deleted'
}

// 用户模型
export class UserModel extends BaseModel implements UserInfo {
    name: string = ''
    email: string = ''
    avatar?: string
    phone?: string
    status: UserStatus = UserStatus.PENDING

    private _password?: string

    constructor(data?: Partial<UserModel>) {
        super(data)
    }

    get displayName(): string {
        return this.name || 'Anonymous'
    }

    set displayName(value: string) {
        this.name = value
    }

    get isActive(): boolean {
        return this.status === UserStatus.ACTIVE
    }

    setPassword(password: string): void {
        this._password = this.hashPassword(password)
        this.touch()
    }

    verifyPassword(password: string): boolean {
        return this._password === this.hashPassword(password)
    }

    private hashPassword(password: string): string {
        // 简化的哈希（实际应使用加密库）
        return `hashed_${password}`
    }

    override toJSON(): object {
        return {
            ...super.toJSON(),
            name: this.name,
            email: this.email,
            avatar: this.avatar,
            phone: this.phone,
            status: this.status
        }
    }

    static override fromJSON(json: object): UserModel {
        return super.fromJSON.call(UserModel, json)
    }
}

// 管理员模型
export class AdminModel extends UserModel {
    role: AdminRole = AdminRole.ADMIN
    permissions: string[] = []

    constructor(data?: Partial<AdminModel>) {
        super(data)
    }

    hasPermission(permission: string): boolean {
        return this.permissions.includes(permission) || this.role === AdminRole.SUPER_ADMIN
    }

    addPermission(permission: string): void {
        if (!this.hasPermission(permission)) {
            this.permissions.push(permission)
            this.touch()
        }
    }

    removePermission(permission: string): void {
        const index = this.permissions.indexOf(permission)
        if (index > -1) {
            this.permissions.splice(index, 1)
            this.touch()
        }
    }

    override toJSON(): object {
        return {
            ...super.toJSON(),
            role: this.role,
            permissions: this.permissions
        }
    }
}

// 管理员角色枚举
export enum AdminRole {
    ADMIN = 'admin',
    SUPER_ADMIN = 'super_admin'
}

// 用户配置接口
export interface UserConfig {
    theme: 'light' | 'dark' | 'auto'
    language: string
    notifications: NotificationConfig
    privacy: PrivacyConfig
}

// 通知配置
export interface NotificationConfig {
    enabled: boolean
    email: boolean
    push: boolean
    sound: boolean
}

// 隐私配置
export interface PrivacyConfig {
    profileVisible: boolean
    activityVisible: boolean
    searchEngineIndexing: boolean
}

// 配置模型
export class ConfigModel implements UserConfig {
    theme: 'light' | 'dark' | 'auto' = 'auto'
    language: string = 'zh-CN'
    notifications: NotificationConfig = {
        enabled: true,
        email: true,
        push: true,
        sound: false
    }
    privacy: PrivacyConfig = {
        profileVisible: true,
        activityVisible: false,
        searchEngineIndexing: false
    }

    updateTheme(theme: 'light' | 'dark' | 'auto'): void {
        this.theme = theme
    }

    updateLanguage(lang: string): void {
        this.language = lang
    }

    updateNotifications(config: Partial<NotificationConfig>): void {
        Object.assign(this.notifications, config)
    }

    updatePrivacy(config: Partial<PrivacyConfig>): void {
        Object.assign(this.privacy, config)
    }

    toJSON(): object {
        return {
            theme: this.theme,
            language: this.language,
            notifications: { ...this.notifications },
            privacy: { ...this.privacy }
        }
    }

    static fromJSON(json: any): ConfigModel {
        const config = new ConfigModel()
        config.theme = json.theme
        config.language = json.language
        config.notifications = { ...config.notifications, ...json.notifications }
        config.privacy = { ...config.privacy, ...json.privacy }
        return config
    }
}

// 分页结果
export interface PaginatedResult<T> {
    items: T[]
    total: number
    page: number
    pageSize: number
    totalPages: number
    hasNext: boolean
    hasPrev: boolean
}

// 分页模型
export class PaginationModel<T> implements PaginatedResult<T> {
    items: T[] = []
    total: number = 0
    page: number = 1
    pageSize: number = 20
    totalPages: number = 0
    hasNext: boolean = false
    hasPrev: boolean = false

    constructor(data?: Partial<PaginationModel<T>>) {
        if (data) {
            Object.assign(this, data)
            this.totalPages = Math.ceil(this.total / this.pageSize)
            this.hasNext = this.page < this.totalPages
            this.hasPrev = this.page > 1
        }
    }

    static async fetchPage<T>(
        fetcher: (page: number, pageSize: number) => Promise<{ items: T[], total: number }>,
        page: number = 1,
        pageSize: number = 20
    ): Promise<PaginationModel<T>> {
        const { items, total } = await fetcher(page, pageSize)
        return new PaginationModel<T>({ items, total, page, pageSize })
    }
}

// 响应模型
export class ResponseModel<T> {
    success: boolean
    data?: T
    error?: string
    message?: string

    private constructor(success: boolean, data?: T, error?: string, message?: string) {
        this.success = success
        this.data = data
        this.error = error
        this.message = message
    }

    static success<T>(data: T, message?: string): ResponseModel<T> {
        return new ResponseModel(true, data, undefined, message)
    }

    static error<T>(error: string, message?: string): ResponseModel<T> {
        return new ResponseModel(false, undefined, error, message)
    }

    isSuccess(): this is { success: true; data: T } {
        return this.success
    }

    isError(): this is { success: false; error: string } {
        return !this.success
    }
}

// 修改于 1779121799.0751863
