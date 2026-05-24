/**
 * 嵌套组件文件 - 深度 23
 */

import { NestedComponent24 } from './NestedComponent24';

@Component
export struct NestedComponent23 {
    build() {
        Column() {
            NestedComponent24()
            NestedComponent24()
        }
    }
}
