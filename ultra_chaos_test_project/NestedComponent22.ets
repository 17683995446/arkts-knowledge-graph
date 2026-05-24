/**
 * 嵌套组件文件 - 深度 22
 */

import { NestedComponent23 } from './NestedComponent23';

@Component
export struct NestedComponent22 {
    build() {
        Column() {
            NestedComponent23()
            NestedComponent23()
        }
    }
}
