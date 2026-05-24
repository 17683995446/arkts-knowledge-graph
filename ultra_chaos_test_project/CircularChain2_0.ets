/**
 * 循环导入链 2, 文件 0
 */

import { Class1 } from './CircularChain2_1';

export class Class0 {
    use1() {
        return new Class1();
    }
}
