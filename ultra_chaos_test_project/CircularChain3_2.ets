/**
 * 循环导入链 3, 文件 2
 */

import { Class0 } from './CircularChain3_0';

export class Class2 {
    use0() {
        return new Class0();
    }
}
