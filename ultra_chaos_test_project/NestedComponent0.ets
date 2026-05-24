/**
 * 嵌套组件文件 - 深度 0
 */

import { NestedComponent1 } from './NestedComponent1';

@Component
export struct NestedComponent0 {
    build() {
        Column() {
            NestedComponent1()
            NestedComponent1()
        }
    }
}
