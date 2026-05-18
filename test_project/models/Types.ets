/**
 * 类型定义文件
 */

// 用户信息
export interface UserInfo {
    id: string
    name: string
    email: string
    avatar?: string
    phone?: string
    status?: UserStatus
    createdAt?: number
    updatedAt?: number
}

// 用户配置
export interface UserConfig {
    theme: 'light' | 'dark' | 'auto'
    language: string
    notifications?: NotificationSettings
}

// 通知设置
export interface NotificationSettings {
    enabled: boolean
    email: boolean
    push: boolean
}

// 用户状态
export enum UserStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    PENDING = 'pending'
}

// 主题
export enum AppTheme {
    LIGHT = 'light',
    DARK = 'dark',
    AUTO = 'auto'
}

// API响应
export interface ApiResponse<T = any> {
    success: boolean
    data?: T
    error?: string
    message?: string
}

// 分页参数
export interface PageParams {
    page: number
    pageSize: number
}

// 分页结果
export interface PageResult<T> {
    items: T[]
    total: number
    page: number
    pageSize: number
}

// 回调类型
export type Callback<T = void> = (data: T) => void
export type AsyncCallback<T = void> = (data: T) => Promise<void>

// 工具类型
export type DeepPartial<T> = {
    [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type Required<T, K extends keyof T> = Omit<T, K> & { [P in K]-?: T[P] }
