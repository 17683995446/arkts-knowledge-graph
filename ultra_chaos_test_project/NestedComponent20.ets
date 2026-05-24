/**
 * 嵌套组件文件 - 深度 20
 */

import { NestedComponent21 } from './NestedComponent21';

@Component
export struct NestedComponent20 {
    build() {
        Column() {
            NestedComponent21()
            NestedComponent21()
        }
    }
}
